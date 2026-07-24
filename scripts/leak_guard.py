"""Fail if tracked filenames look like user content or credentials."""

from __future__ import annotations

import subprocess
import sys

FORBIDDEN_PREFIXES = ("artifacts/", "output/", "cache/", "staged_blobs/", "page_images/")
FORBIDDEN_NAMES = {".env"}
FORBIDDEN_SUFFIXES = (".pdf", ".jsonl")


def main() -> int:
    tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    violations = [
        path
        for path in tracked
        if path in FORBIDDEN_NAMES
        or path.startswith(FORBIDDEN_PREFIXES)
        or path.endswith(FORBIDDEN_SUFFIXES)
    ]
    if violations:
        print("Tracked user-content or credential-like files are forbidden:", file=sys.stderr)
        print("\n".join(violations), file=sys.stderr)
        return 1
    print("Leak guard passed: no tracked artifacts, PDFs, JSONL exports, or .env files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
