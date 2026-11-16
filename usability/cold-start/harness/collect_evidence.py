"""
collect_evidence.py: copy a run's files into the repository, with local paths replaced.

A transcript records absolute paths on the machine that ran it, such as the agent's working
folder and the files it read or wrote. Those paths can name the local account. This script
copies each named file, replaces each given local path with a placeholder, and stops if a
forbidden string remains in any copy. Beside the copies it writes MANIFEST.json: for each
file, the SHA-256 of the original and of the copy, and the number of replacements made.
Nothing else in a file changes. It uses the standard library only.

Usage:
    python collect_evidence.py --dest ../run-1 \
        --replace "/path/to/run-1=<run-dir>" --forbid "/Users/" \
        /path/to/run-1/run.json=run.json /path/to/wire.jsonl=wire.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(data: bytes) -> str:
    """The SHA-256 of some bytes."""
    return hashlib.sha256(data).hexdigest()


def redact(text: str, replacements: list[tuple[str, str]]) -> tuple[str, int]:
    """Apply each (old, new) replacement, longest old first; return the text and the count made."""
    count = 0
    for old, new in sorted(replacements, key=lambda pair: len(pair[0]), reverse=True):
        count += text.count(old)
        text = text.replace(old, new)
    return text, count


def main(argv: list[str] | None = None) -> int:
    """Copy each SOURCE=NAME file to --dest/NAME with replacements, then write MANIFEST.json."""
    parser = argparse.ArgumentParser(description="Copy a run's files into the repository, local paths replaced.")
    parser.add_argument("--dest", required=True, type=Path, help="the folder to copy into")
    parser.add_argument("--replace", action="append", default=[], help="OLD=NEW: a local path and its placeholder")
    parser.add_argument("--forbid", action="append", default=[],
                        help="a string that must not remain in any copy, compared without regard to case")
    parser.add_argument("files", nargs="+", help="SOURCE=NAME, where NAME is the copy's path under --dest")
    args = parser.parse_args(argv)

    replacements = [tuple(spec.split("=", 1)) for spec in args.replace]
    if any(len(pair) != 2 or not pair[0] for pair in replacements):
        parser.error("each --replace must be OLD=NEW with a non-empty OLD")
    copies: dict[str, tuple[bytes, bytes, int]] = {}
    for spec in args.files:
        source, _, name = spec.rpartition("=")
        if not source or not name:
            parser.error(f"not SOURCE=NAME: {spec}")
        original = Path(source).read_bytes()
        text, count = redact(original.decode("utf-8"), replacements)
        remaining = [word for word in args.forbid if word.lower() in text.lower()]
        if remaining:
            raise SystemExit(f"{name} still contains {remaining}; nothing was written")
        copies[name] = (original, text.encode("utf-8"), count)

    for name, (_, copy, _) in copies.items():  # write only after every file has passed
        target = args.dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(copy)
    manifest = {
        "placeholders": sorted({new for _, new in replacements}),
        "files": {name: {"sha256_original": _sha256(original), "sha256_copy": _sha256(copy), "replacements": count}
                  for name, (original, copy, count) in sorted(copies.items())},
    }
    (args.dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: entry["replacements"] for name, entry in manifest["files"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
