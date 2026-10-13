# GitHub draft PR workflow check

This documentation-only change checks the cloud agent's branch, push and draft pull request workflow after the repository added `AGENTS.md`.

- Repository instructions were retrieved from `main` at `5cdfd84e` and read before this change.
- Work uses a dedicated branch and targets `main` through a draft pull request.
- No application, dependency, database or deployment changes are included.
- This check does not validate browser rendering. Chromium is needed for the pending visual review; its sandbox must remain enabled.

This is a disposable workflow-check candidate for review, with no automatic merge.

## Actions-based draft creation

The `auto-draft-pr.yml` workflow now opens a draft for the branch that triggered
its push event, targeting the repository's default branch. It checks for an
existing open PR and serializes runs for the same branch. It does not generate
another branch, commit changes, push to main or merge PRs.

The runner uses its repository-scoped `GITHUB_TOKEN` with `pull-requests: write`
and `contents: read`. GitHub must permit Actions to create pull requests in the
repository settings; this change does not modify that setting. A successful
push alone does not prove the workflow ran or that a PR was created. Check the
**Auto Create Draft PR** run and the Pull Requests tab to confirm the result.

Local validation (2026-10-14): workflow YAML parsing and Bash syntax passed;
the full Python suite passed with **147 passed, 0 failed, 0 skipped**. Three new
mocked-runner tests cover creation, an existing PR, and API-list failure. The
Docker context includes this one additional source workflow for those tests;
other workflow files, secrets and research data remain excluded. No new Docker
engine execution is claimed.
