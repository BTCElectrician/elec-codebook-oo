# Releasing

Use this checklist for a public release. A version entry is not a GitHub Release until the annotated
tag and GitHub Release both exist. Do not push, tag remotely, or create a GitHub Release without
operator approval.

1. Choose the semantic version and update matching package-version values in `pyproject.toml` and
   `codebook_agent/__init__.py`. Update the README version badge and capability claims when needed.
2. Move the verified changes from `CHANGELOG.md`'s `Unreleased` section into a dated version entry.
   Link each entry to the supporting commit or pull request; do not claim a release that has not
   been tagged.
3. Update `STATUS.md` to describe current implemented and not-implemented behavior, rather than
   copying release history into it. Update the agent contract and focused tests if a command,
   output, capability, or safety boundary changed.
4. Run focused tests, then `make check` and `git diff --check`. Run `make test-ocr` and the
   disposable `make pgvector-up && make test-pgvector && make pgvector-down` lanes when the release
   changes those capabilities.
5. Commit the release preparation and verify the exact commit SHA and clean worktree. After
   operator approval, create and inspect an annotated tag at that SHA:

   ```bash
   git tag -a vX.Y.Z <commit-sha> -m "vX.Y.Z"
   git show vX.Y.Z --stat
   ```

6. After separate approval to publish, push the reviewed commit and tag, then create the GitHub
   Release from the tag. This repository has no package artifact workflow yet, so do not attach an
   invented binary or wheel.

   ```bash
   git push origin <branch>
   git push origin vX.Y.Z
   gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes
   ```

7. Verify GitHub resolves the tag and release to the intended SHA, confirm CI for that SHA, and
   update `CHANGELOG.md` links if necessary. Record the proof in the task handoff, not by appending
   a release diary to `STATUS.md`.
