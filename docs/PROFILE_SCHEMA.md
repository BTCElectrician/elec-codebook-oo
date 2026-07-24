# Profile schema

Profiles are JSON metadata, never extracted book content. Required fields are `id`, `title`,
`document_type`, `backend`, and `questions`. The only accepted backend in v0.1 is
`local-artifacts`. Optional fields include `edition`, `legal_use_required`, `content_ranges`, and
`printed_page_offset`.

Copy `codebook_agent/profiles/nfpa70-reference-template.json` to start an electrical-codebook
profile. Replace placeholders with metadata about your authorized document; do not paste chapters,
tables, or source text into the profile.
