"""
run_local_probe.py: run probe_refusals.py against this checkout's own record, on loopback.

It starts the real service from this checkout on an ephemeral loopback port, with the
synthetic household and locally generated signing keys (the worked example's offline
wiring), mints a token for the facility's shift agent, and runs the probe. Nothing leaves
127.0.0.1, and the token is never printed or written.

Usage, from the repository root:
    python usability/bad-argument/run_local_probe.py --out usability/bad-argument/after/local-branch-probe.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.run_worked_example import LocalRecord  # noqa: E402  (after the path is set)


def _probe_module():
    """Load probe_refusals.py beside this file; its folder name is not a package name."""
    spec = importlib.util.spec_from_file_location("probe_refusals", Path(__file__).with_name("probe_refusals.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    """Start the local record, probe it as the shift agent, and write the results."""
    parser = argparse.ArgumentParser(description="Probe this checkout's record on loopback.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    probe = _probe_module()
    with tempfile.TemporaryDirectory(prefix="bad-argument-") as workdir:
        record = LocalRecord(Path(workdir))
        try:
            report = probe.run(f"{record.base_url}/mcp", record.tokens("shift").bearer())
        finally:
            record.close()
    report["record"] = "this checkout, on loopback, with the synthetic household"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for row in report["cases"]:
        answer = row["answer"]
        shown = {k: answer.get(k) for k in ("ok", "reason", "argument", "problem") if k in answer}
        print(f"{row['case']:<52} {row['http_status']} {json.dumps(shown)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
