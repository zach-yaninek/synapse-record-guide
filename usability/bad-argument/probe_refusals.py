"""
probe_refusals.py: send the record a fixed set of malformed calls and keep what it answers.

Part 3 of the usability test. The guide's known limits say an `invalid_request` refusal
doesn't say which argument failed. This probe makes that limit observable: each case below
breaks one rule of a tool's published input schema, as a caller starting cold might, and the
probe records the record's refusal. One case breaks a rule the schema does not publish (a
date in the right format that does not exist), to show where naming the argument stops. A
well-formed `my_grants` call comes first, to show the caller's access works.

It speaks MCP's JSON-RPC over HTTP to one URL. Against the hosted record, that URL is the
loopback token proxy, which adds the shift agent's credentials; the probe never sees one.
Against a local record, the caller passes a bearer token in an environment variable, which
is never printed or written. It uses the standard library only.

Usage:
    python probe_refusals.py --url http://127.0.0.1:8798/mcp --out before/probe.json
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PERSON = "person-a"
BRIEF = {"person_id": PERSON, "purpose": "shift_handoff", "item_kinds": ["mobility"]}

# The record's eating claim for person-a as the hosted record returned it on November 15th,
# 2026 (synthetic data). Every case below that uses it changes exactly one field.
CLAIM: dict[str, Any] = {
    "item_kind": "eating",
    "status": "differing_accounts",
    "entries": [
        {"entry_id": 1, "item_kind": "eating", "basis": "reported",
         "effective_time": "2026-09-20T15:00:00Z", "recorded_time": "2026-09-20T15:10:00Z",
         "entered_time": "2026-09-20T15:10:05Z", "author_agent_id": "agent-family",
         "author_operator": "The family", "author_operator_kind": "family", "author_operator_domain": None,
         "author_domain_verified": False,
         "untrusted": {"value": "Eats a full breakfast most days; lunch is small; dislikes spicy food; drinks "
                                "about four glasses of water a day when reminded.",
                       "quote": None, "source_ref": None, "informant_role": "daughter", "informant_key": None,
                       "trust": "untrusted_source_text"},
         "author_principal_id": "user-daughter-a", "scheduled_for": None, "media_ids": []},
        {"entry_id": 7, "item_kind": "eating", "basis": "observed",
         "effective_time": "2026-10-10T13:00:00Z", "recorded_time": "2026-10-10T13:20:00Z",
         "entered_time": "2026-10-10T13:20:15Z", "author_agent_id": "agent-gardens-notes",
         "author_operator": "Example Gardens Assisted Living", "author_operator_kind": "facility",
         "author_operator_domain": "examplegardens.test", "author_domain_verified": True,
         "untrusted": {"value": "Ate most of breakfast and about half of lunch; drank two cups of water.",
                       "quote": None, "source_ref": "aide-note:EXG-2026-10-10-1300", "informant_role": "aide",
                       "informant_key": None, "trust": "untrusted_source_text"},
         "author_principal_id": "org-example-gardens", "scheduled_for": None, "media_ids": []},
    ],
}


def _brief(**changes: Any) -> dict[str, Any]:
    """request_brief's arguments with some changed; a value of None removes that argument."""
    arguments = {**BRIEF, **changes}
    return {key: value for key, value in arguments.items() if value is not None}


def _claim(change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """check_claims' arguments, citing a copy of CLAIM with one change."""
    claim = copy.deepcopy(CLAIM)
    change(claim)
    return {"person_id": PERSON, "purpose": "shift_handoff", "claims": [claim]}


def _set(path: tuple[Any, ...], value: Any) -> Callable[[dict[str, Any]], None]:
    """A change that sets one field of a claim, found by its path."""
    def change(claim: dict[str, Any]) -> None:
        target = claim
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = value
    return change


# (name, tool, arguments, the published rule it breaks, or None when the schema does not publish it)
CASES: list[tuple[str, str, dict[str, Any], str | None]] = [
    ("a well-formed call (control)", "my_grants", {"person_id": PERSON}, None),
    ("purpose is not a published purpose", "request_brief", _brief(purpose="handoff"), "enum"),
    ("item kind capitalized", "request_brief", _brief(item_kinds=["Mobility"]), "enum"),
    ("purpose left out", "request_brief", _brief(purpose=None), "required"),
    ("item kinds sent as a string", "request_brief", _brief(item_kinds="mobility"), "type"),
    ("an argument the tool does not take", "request_brief", {**BRIEF, "kinds": ["mobility"]},
     "additionalProperties"),
    ("no item kinds", "request_brief", _brief(item_kinds=[]), "minItems"),
    ("an item kind twice", "request_brief", _brief(item_kinds=["eating", "eating"]), "uniqueItems"),
    ("a negative cursor", "request_brief", _brief(since_cursor=-1), "minimum"),
    ("a cited entry id sent as text", "check_claims", _claim(_set(("entries", 1, "entry_id"), "7")), "type"),
    ("a date in the published format that does not exist", "check_claims",
     _claim(_set(("entries", 1, "effective_time"), "2026-02-30T13:00:00Z")), None),
]


def call(url: str, tool: str, arguments: dict[str, Any], bearer: str | None) -> dict[str, Any]:
    """One tools/call; returns the HTTP status, MCP's isError, and the record's parsed answer."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": "2025-11-25"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    answer = json.loads(raw)
    result = answer.get("result") or {}
    content = result.get("content") or [{}]
    return {"http_status": status, "is_error": result.get("isError"),
            "answer": json.loads(content[0]["text"]) if "text" in content[0] else answer}


def run(url: str, bearer: str | None = None) -> dict[str, Any]:
    """Every case, in order, with what was sent and what came back."""
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = []
    for name, tool, arguments, rule in CASES:
        outcome = call(url, tool, arguments, bearer)
        answer = outcome["answer"]
        results.append({"case": name, "tool": tool, "breaks": rule, "arguments": arguments, **outcome,
                        "names_argument": isinstance(answer, dict) and "argument" in answer})
    return {"started_at": started, "url_kind": "loopback", "cases": results}


def main(argv: list[str] | None = None) -> int:
    """Run the probe once and write its results as JSON."""
    parser = argparse.ArgumentParser(description="Probe the record's invalid_request refusals.")
    parser.add_argument("--url", required=True, help="the record's /mcp URL, or the loopback token proxy's")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--bearer-env", help="an environment variable holding a bearer token (local records only)")
    args = parser.parse_args(argv)
    bearer = os.environ.get(args.bearer_env) if args.bearer_env else None
    report = run(args.url, bearer)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for row in report["cases"]:
        answer = row["answer"]
        shown = {k: answer.get(k) for k in ("ok", "reason", "argument", "problem") if k in answer}
        print(f"{row['case']:<52} {row['http_status']} {json.dumps(shown)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
