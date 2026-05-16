---
name: Clean up orphans from own changes
description: When a change makes an import/variable/function unused, remove it — but do not touch pre-existing orphans
type: feedback
---

**Rule:** When your changes create orphans (unused imports, variables, or functions), remove them. Do not remove pre-existing dead code that your change did not create.

**Why:** The CLAUDE.md "Surgical Changes" rule states: "When your changes create orphans: Remove imports/variables/functions that YOUR changes made unused. Don't remove pre-existing dead code unless asked."

**How to apply:** After any deletion or refactor, grep for the removed symbol's usage within the same file. If the only usage was in the removed code, clean up the declaration/import.
