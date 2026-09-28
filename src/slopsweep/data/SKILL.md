---
name: slopsweep
description: Manual workspace sweep and triage for slopsweep-managed agent sessions.
---

# slopsweep skill

Use when finishing work in a slopsweep session directory.

## Before you stop

1. Run `slopsweep manifest add` for every non-tmp file you created.
2. Mark unneeded artifacts as `discard`.
3. Remove large scratch data from `tmp/` if still needed for the task.

## Periodic cleanup

- `slopsweep run` — dry-run plan (default).
- `slopsweep run --apply` — move discards and stale scratch to trash, archive old outputs, purge old trash.

## Ambiguous files

- `slopsweep triage` — write `triage.jsonl` (metadata only).
- Feed `docs/triage-prompt.md` to your model; save JSONL labels.
- `slopsweep apply-labels labels.jsonl` — validate (dry-run).
- `slopsweep apply-labels labels.jsonl --apply` — apply validated labels.

## Rules for agents

Run `slopsweep rules` and keep that block in your agent instructions.
