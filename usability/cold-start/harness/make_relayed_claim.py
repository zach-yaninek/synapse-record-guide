"""
make_relayed_claim.py: read the record as the shift agent before the run, and make the relayed claim.

Before the cold-start run, this script:
  1. asks the record, through the loopback token proxy, for a shift-handoff brief on
     person-a's mobility and eating, and saves the whole answer as the pre-run snapshot;
  2. takes the eating claim and changes one phrase in one account's value, the way a claim
     can drift as one agent passes it to another, and saves the result as the relayed claim;
  3. checks both the unchanged claim and the relayed claim with check_claims, and saves
     the answers, so the run is scored against what the record itself said.

The change is printed here and stated in the preregistration. The agent is not told of it.
It calls the token proxy directly, not the recorder, so the recorder's log holds the
agent's exchanges only. It uses the standard library only.

Usage:
    python make_relayed_claim.py --proxy http://127.0.0.1:8799/mcp --out-dir ../setup \
        --find "about half of lunch" --replace "all of lunch"
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PERSON, PURPOSE, KINDS = "person-a", "shift_handoff", ["mobility", "eating"]


def call(proxy: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """One tools/call through the token proxy; returns the parsed {"ok", ...} tool result."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    request = urllib.request.Request(proxy, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Accept": "application/json",
                                              "MCP-Protocol-Version": "2025-06-18"})
    with urllib.request.urlopen(request, timeout=60) as response:
        answer = json.loads(response.read())
    return json.loads(answer["result"]["content"][0]["text"])


def _write(path: Path, data: Any) -> str:
    """Write pretty JSON and return its SHA-256."""
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> None:
    """Snapshot the brief, write the relayed claim, and record what check_claims says of both."""
    parser = argparse.ArgumentParser(description="Make the cold-start run's relayed claim.")
    parser.add_argument("--proxy", default="http://127.0.0.1:8799/mcp")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--find", required=True, help="the phrase to change in one facility account")
    parser.add_argument("--replace", required=True)
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    brief = call(args.proxy, "request_brief", {"person_id": PERSON, "purpose": PURPOSE, "item_kinds": KINDS})
    if not brief.get("ok"):
        raise SystemExit(f"the brief was refused: {brief}")
    claims = {claim["item_kind"]: claim for claim in brief["result"]["claims"]}
    eating = claims["eating"]
    relayed = copy.deepcopy(eating)
    hits = [entry for entry in relayed["entries"]
            if entry["author_operator_kind"] == "facility" and args.find in entry["untrusted"]["value"]]
    if len(hits) != 1 or hits[0]["untrusted"]["value"].count(args.find) != 1:
        raise SystemExit("the phrase must occur exactly once, in exactly one facility account")
    changed = hits[0]
    before = changed["untrusted"]["value"]
    changed["untrusted"]["value"] = before.replace(args.find, args.replace)

    unchanged_check = call(args.proxy, "check_claims", {"person_id": PERSON, "purpose": PURPOSE, "claims": [eating]})
    relayed_check = call(args.proxy, "check_claims", {"person_id": PERSON, "purpose": PURPOSE, "claims": [relayed]})
    hashes = {
        "brief-before-run.json": _write(args.out_dir / "brief-before-run.json", {"requested_at": at, "answer": brief}),
        "relayed-claim.json": _write(args.out_dir / "relayed-claim.json", relayed),
        "checks-before-run.json": _write(args.out_dir / "checks-before-run.json",
                                         {"unchanged_claim": unchanged_check, "relayed_claim": relayed_check}),
    }
    print(json.dumps({
        "requested_at": at,
        "statuses": {kind: claim["status"] for kind, claim in claims.items()},
        "standing_entries": {kind: [e["entry_id"] for e in claim["entries"]] for kind, claim in claims.items()},
        "changed_entry": changed["entry_id"], "value_before": before, "value_relayed": changed["untrusted"]["value"],
        "unchanged_claim_check": unchanged_check.get("result", unchanged_check),
        "relayed_claim_check": relayed_check.get("result", relayed_check),
        "sha256": hashes,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
