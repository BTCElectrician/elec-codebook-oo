"""Regenerate the text-only synthetic input; no real book or PDF is included."""

from pathlib import Path

SOURCE = Path(__file__).with_name("source.txt")
SOURCE.write_text(
    "Synthetic Electrical Handbook\n\n"
    "Article 1. A branch circuit is a circuit that supplies one or more outlets. "
    "This synthetic text is not a code requirement.\n\n"
    "Table 1. Training values only: a small example row contains 20 amperes and a fictional conductor label.\n",
    encoding="utf-8",
)
print(f"Wrote synthetic source: {SOURCE}")
