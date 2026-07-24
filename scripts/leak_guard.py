"""Fail if tracked or unignored filenames look like user content or credentials."""

from __future__ import annotations

import subprocess
import sys
from pathlib import PurePosixPath

FORBIDDEN_DIRECTORY_NAMES = {"artifacts", "output", "cache", "staged_blobs", "page_images"}
FORBIDDEN_SUFFIXES = (".pdf", ".jsonl")


def is_forbidden(path: str) -> bool:
    candidate = PurePosixPath(path)
    name = candidate.name.lower()
    return (
        name == ".env"
        or (name.startswith(".env.") and name != ".env.example")
        or any(part.lower() in FORBIDDEN_DIRECTORY_NAMES for part in candidate.parts[:-1])
        or name.endswith(FORBIDDEN_SUFFIXES)
    )


def main() -> int:
    candidates = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        text=True,
    ).splitlines()
    violations = [path for path in candidates if is_forbidden(path)]
    if violations:
        print(
            "Tracked or unignored user-content and credential-like files are forbidden:",
            file=sys.stderr,
        )
        print("\n".join(violations), file=sys.stderr)
        return 1
    print(
        "Leak guard passed: no tracked or unignored artifacts, PDFs, "
        "JSONL exports, or .env files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
