# GitHub draft PR workflow check

This documentation-only change checks the cloud agent's branch, push and draft pull request workflow after the repository added `AGENTS.md`.

- Repository instructions were retrieved from `main` at `5cdfd84e` and read before this change.
- Work uses a dedicated branch and targets `main` through a draft pull request.
- No application, dependency, database or deployment changes are included.
- This check does not validate browser rendering. Chromium is needed for the pending visual review; its sandbox must remain enabled.

This is a disposable workflow-check candidate for review, with no automatic merge.
