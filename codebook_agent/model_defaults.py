"""Default model names, kept in one place.

To adopt a newer model, change the constant here, run `make check`, and update
the "Verified" date. Profiles, the CLI, plan output, and the README example all
read or are tested against these values, so no other file needs editing. A
profile or command-line flag that names a model explicitly still wins.

Verified 2026-10-02 against the provider's published model list:
- correction: OCR repair is a focused, high-volume, per-page task, so it uses
  the provider's efficient tier. Every correction is still gated by
  protected-token, similarity, and length checks before acceptance.
- synthesis: answers are written from retrieved evidence and must cite it, so
  this uses the provider's balanced high-capability tier.
- embeddings: index and query must use the same model. Changing this default
  affects only new corpora; an existing pgvector corpus keeps the model it was
  indexed with, and queries use that stored model.
"""

from __future__ import annotations

MODELS_VERIFIED_ON = "2026-10-02"

DEFAULT_CORRECTION_MODEL = "gpt-6-luna"
DEFAULT_SYNTHESIS_MODEL = "gpt-6.1-sol"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
HASH_EMBEDDING_MODEL = "codebook-hash-v1"

DEFAULT_MODELS = {
    "correction": {"provider": "openai", "model": DEFAULT_CORRECTION_MODEL},
    "synthesis": {"provider": "openai", "model": DEFAULT_SYNTHESIS_MODEL},
    "embedding": {"provider": "openai", "model": DEFAULT_OPENAI_EMBEDDING_MODEL},
    "offline_embedding": {"provider": "hash", "model": HASH_EMBEDDING_MODEL},
}
