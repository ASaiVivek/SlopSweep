# Changelog

## v0.1.1 (unreleased)

### Fixed

- `session end` uses `SLOPSWEEP_SESSION` when `--id` is omitted (hooks/quickstart).
- `apply-labels --apply` writes JSONL audit entries for keep/trash/archive actions.

### Tests

- Newline filenames, active-session scratch TTL, audit log, git label rejection, multi-line label validation.

## v0.1.0 (2025-09-28)

### Added

- CLI: `init`, `session`, `manifest`, `run`, `status`, `triage`, `apply-labels`, `rules`, `hooks print`
- Safety: root guard, containment, symlink leaves, git work-tree skip, run lock
- Planner/executor for manifest discards, stale scratch, verified output archives, trash purge
- Metadata-only triage and validated label application
- Packaged agent rules, skill, and hook/cron examples
- CI on Linux and macOS for Python 3.11–3.13

### Notes

- PyPI publish intentionally deferred pending package name confirmation.
