# LitBeacon after 1.0 — roadmap draft

This is a planning draft, not the active release roadmap. [Gate 6](../../../ROADMAP.md#gate-6--versioning-documentation-and-release-artifact-p0) stays open until the published asset and public distribution checks are complete. No feature scope or release date is approved here.

1. **Finish public 1.0 distribution.** Inspect and install the exact uploaded wheel and `SETUP.txt`, include the chosen MIT license with the public source and release, make release notes useful to a fresh user, and verify an unauthenticated download after the owner changes visibility. The owner reported a history review with no personal data found; record the account-billing CI exception and native macOS limit honestly.
2. **Triage real 1.0 feedback.** Take specific reproducible reports from local Windows, macOS and Linux use; prioritize data integrity, installation, recovery and compatibility. Use small draft PRs with a focused test and user-visible fix.
3. **Improve verification when available.** Restore hosted CI once account billing permits and run native platform checks, especially macOS. Keep user-reported results separate from automated evidence.

Archive the [1.0 release roadmap](../../../ROADMAP.md) and promote a reviewed post-1.0 roadmap only after Gate 6 is closed. Major features, public web hosting and new provider/model integrations require separate scope decisions.
