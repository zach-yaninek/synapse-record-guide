"""
run_cold_start.py: run one cold-start session of a fresh Claude Code agent against the record.

The agent is given three things and nothing else:
  * the guide, copied into an otherwise empty working folder as AGENT-GUIDE.md;
  * the relayed claim, copied beside it as relayed-claim.json;
  * the task (harness/task.md) as its prompt.
It reaches the record only through the recorder's loopback URL (harness/mcp.json). The token
proxy behind the recorder holds the record credentials, so the agent never sees one.

Claude Code runs headless (-p), in a fresh, empty home folder, with these flags:
  --bare        no CLAUDE.md discovery, memory, hooks, plugins, or keychain; API-key auth only
  --restricted  no shell or code-running tools, no web fetch; file tools confined to the folder
  --strict-mcp-config --mcp-config harness/mcp.json    the record's MCP server and no other
  --tools Read,Write,Edit,Glob,Grep --allowedTools mcp__record
                (under --bare only Read and Edit take effect; Edit also creates files.
                 See the dated note in PREREGISTRATION.md.)
  --permission-mode acceptEdits --permission-prompts none    nobody answers a prompt
  --disable-slash-commands --no-session-persistence --max-budget-usd <cap>
  --output-format stream-json --verbose    every event, saved as the transcript

The model key comes from the ANTHROPIC_API_KEY line of a key file. It is passed only in the
child's environment: never printed, logged, or put on a command line. A run folder is never
reused; the script stops if it exists.

Usage:
    python run_cold_start.py --claude /path/to/claude --key-file /path/to/env-file \
        --run-dir /path/to/run-1 --guide /path/to/AGENT-GUIDE.md --claim /path/to/relayed-claim.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
TOOLS = "Read,Write,Edit,Glob,Grep"


def _now() -> str:
    """The current UTC time, to the second."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    """The SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_key(key_file: Path) -> str:
    """The ANTHROPIC_API_KEY value from a KEY=value file, without its quotes; the empty string if absent."""
    for line in key_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip().strip("'\"")
    return ""


def claude_arguments(claude: str, task: str, model: str, budget: str, mcp_config: Path) -> list[str]:
    """The exact command line for the agent, prompt included."""
    return [
        claude, "-p", task,
        "--bare", "--restricted", "--model", model,
        "--strict-mcp-config", "--mcp-config", str(mcp_config),
        "--tools", TOOLS, "--allowedTools", "mcp__record",
        "--permission-mode", "acceptEdits", "--permission-prompts", "none",
        "--disable-slash-commands", "--no-session-persistence",
        "--max-budget-usd", budget,
        "--output-format", "stream-json", "--verbose",
    ]


def main(argv: list[str] | None = None) -> int:
    """Set up a fresh run folder, run the agent once, and write run.json beside its outputs."""
    parser = argparse.ArgumentParser(description="Run one cold-start session against the record.")
    parser.add_argument("--claude", required=True, help="the Claude Code executable")
    parser.add_argument("--key-file", required=True, type=Path, help="a file with an ANTHROPIC_API_KEY= line")
    parser.add_argument("--run-dir", required=True, type=Path, help="a new folder for this run")
    parser.add_argument("--guide", required=True, type=Path)
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--task", type=Path, default=HARNESS / "task.md")
    parser.add_argument("--mcp-config", type=Path, default=HARNESS / "mcp.json")
    parser.add_argument("--model", default="claude-sonnet-5-5")
    parser.add_argument("--budget-usd", default="3")
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    args = parser.parse_args(argv)

    key = _read_key(args.key_file)
    if not key:
        parser.error("the key file has no ANTHROPIC_API_KEY value")
    run_dir = args.run_dir.resolve()
    work, home = run_dir / "work", run_dir / "home"
    run_dir.mkdir(parents=True, exist_ok=False)  # never reuse a run folder
    work.mkdir()
    home.mkdir()
    shutil.copyfile(args.guide, work / "AGENT-GUIDE.md")
    shutil.copyfile(args.claim, work / "relayed-claim.json")

    base_env = {"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "TMPDIR": str(home), "LANG": "en_US.UTF-8"}
    version = subprocess.run([args.claude, "--version"], env=base_env, capture_output=True, text=True, timeout=60)
    task = args.task.read_text(encoding="utf-8")
    mcp_config = str(args.mcp_config.resolve())
    command = claude_arguments(args.claude, task, args.model, args.budget_usd, Path(mcp_config))
    # The recorded command names the task and MCP config by file, not by text or local path.
    shown = {task: f"<the text of {args.task.name}>", mcp_config: args.mcp_config.name}

    record = {
        "started_at": _now(), "claude_version": version.stdout.strip(), "model": args.model,
        "budget_usd": args.budget_usd, "timeout_seconds": args.timeout_seconds,
        "command": ["claude", *[shown.get(part, part) for part in command[1:]]],
        "environment_names": sorted([*base_env, "ANTHROPIC_API_KEY"]),
        "sha256": {"AGENT-GUIDE.md": _sha256(work / "AGENT-GUIDE.md"),
                   "relayed-claim.json": _sha256(work / "relayed-claim.json"),
                   "task": _sha256(args.task), "mcp-config": _sha256(args.mcp_config)},
    }
    timed_out = False
    with open(run_dir / "transcript.stream.jsonl", "wb") as out, open(run_dir / "stderr.txt", "wb") as err:
        try:
            completed = subprocess.run(command, cwd=work, env={**base_env, "ANTHROPIC_API_KEY": key},
                                       stdout=out, stderr=err, timeout=args.timeout_seconds)
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            timed_out, exit_code = True, None
    record.update({
        "ended_at": _now(), "exit_code": exit_code, "timed_out": timed_out,
        "work_files_after": {p.name: p.stat().st_size for p in sorted(work.iterdir()) if p.is_file()},
    })
    (run_dir / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key_: record[key_] for key_ in ("started_at", "ended_at", "exit_code", "timed_out",
                                                       "work_files_after")}))
    return 0 if exit_code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
