"""
probe_tools.py: report which built-in tools Claude Code offers under a set of flags, at no cost.

Claude Code prints its init event, which lists the session's tools, before its first request to
the model. This script starts it with a deliberately invalid model key, so that request is
refused and nothing is spent, and prints the tools named in the init event. Each probe gets a
new, empty home and working folder under --scratch, and no MCP server, so nothing reaches the
record.

It was written after the isolation check showed fewer file tools than the preregistration
listed. Its results are in results.txt beside it.

Usage:
    python probe_tools.py --claude /path/to/claude --scratch /path/to/empty-folder > results.txt
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

PROBES = [
    ("--bare --restricted --tools Read,Write,Edit,Glob,Grep (the harness)",
     ["--bare", "--restricted", "--tools", "Read,Write,Edit,Glob,Grep"]),
    ("--bare --tools Read,Write,Edit,Glob,Grep", ["--bare", "--tools", "Read,Write,Edit,Glob,Grep"]),
    ("--bare --restricted --tools default", ["--bare", "--restricted", "--tools", "default"]),
    ("--bare --tools default", ["--bare", "--tools", "default"]),
    ("--bare --restricted --tools Write", ["--bare", "--restricted", "--tools", "Write"]),
]
INVALID_KEY = "not-a-real-key"


def probe(claude: str, scratch: Path, flags: list[str]) -> dict:
    """Run one probe and return the init event's tools and how the session ended."""
    home = Path(tempfile.mkdtemp(dir=scratch, prefix="home."))
    work = Path(tempfile.mkdtemp(dir=scratch, prefix="work."))
    no_mcp = scratch / "no-mcp.json"
    no_mcp.write_text('{"mcpServers": {}}\n', encoding="utf-8")
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "TMPDIR": str(home),
           "LANG": "en_US.UTF-8", "ANTHROPIC_API_KEY": INVALID_KEY}
    command = [claude, "-p", "probe", *flags, "--strict-mcp-config", "--mcp-config", str(no_mcp),
               "--permission-mode", "acceptEdits", "--permission-prompts", "none", "--no-session-persistence",
               "--output-format", "stream-json", "--verbose"]
    completed = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=120)
    found: dict = {"tools": None, "ended": None, "cost_usd": None}
    for line in completed.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            found["tools"] = event.get("tools")
        elif event.get("type") == "result":
            found["ended"] = (event.get("result") or "")[:60]
            found["cost_usd"] = event.get("total_cost_usd")
    return found


def main(argv: list[str] | None = None) -> int:
    """Run every probe and print one line of JSON for each."""
    parser = argparse.ArgumentParser(description="Report Claude Code's tools under several flag sets, at no cost.")
    parser.add_argument("--claude", required=True, help="the Claude Code executable")
    parser.add_argument("--scratch", required=True, type=Path, help="an empty folder for the probes' homes")
    args = parser.parse_args(argv)
    home = Path(tempfile.mkdtemp(dir=args.scratch, prefix="home."))
    clean = {"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "TMPDIR": str(home), "LANG": "en_US.UTF-8"}
    version = subprocess.run([args.claude, "--version"], env=clean, capture_output=True, text=True,
                             timeout=60).stdout.strip()
    print(json.dumps({"claude_version": version}))
    for label, flags in PROBES:
        print(json.dumps({"flags": label, **probe(args.claude, args.scratch, flags)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
