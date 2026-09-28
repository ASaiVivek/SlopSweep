# slopsweep

**Stop AI coding agents from bloating disk with junk files—and reclaim the space they already used.**

## The problem

Agents create scratch notes, duplicate reports, screenshots, and “final_v2” copies outside your repo. That clutter piles up silently in the workspace directory you gave them.

## Before / after

| Before | After |
|--------|-------|
| `~/agent-work` grows by gigabytes of summaries and tmp artifacts | Session `tmp/` is swept on a TTL; discards go to dated trash |
| Deliverables mixed with junk | `outputs/` archived after retention; ambiguous files triaged from metadata only |

Example: a week of Codex sessions left **4.2 GB** in `~/agent-work`; after `slopsweep run --apply`, **3.8 GB** moved to trash/archive with a full JSONL audit trail.

## Quickstart (60 seconds)

```bash
pipx install .   # or: uvx pip install .
slopsweep init --root ~/agent-work
eval "$(slopsweep session new)"
# point your agent at $TMPDIR and log files with manifest add
slopsweep session end
slopsweep run          # dry-run plan
slopsweep run --apply  # trash, archive, purge per policy
```

## Safety model

- **Dry-run by default** — pass `--apply` to mutate disk.
- **Trash first** — deletes land in `.trash/<date>/` and are purged after `trash_ttl_days`.
- **Outputs archived, never silently deleted** — verified `tar.gz` before originals are removed.
- **Containment** — paths must stay inside the marked root; symlinks are leaves.
- **Root guard** — requires `.slopsweep-root`; refuses `/` and `$HOME`.
- **No network, no telemetry.**

Details: [docs/safety-model.md](docs/safety-model.md).

## Three layers

1. **Rules** (`slopsweep rules`) — always-on agent instructions (scratch vs outputs, manifest logging).
2. **Deterministic cleanup** (`slopsweep run`) — manifest discards, stale scratch, old outputs, trash purge.
3. **LLM triage** (`slopsweep triage` + `apply-labels`) — metadata-only hints; labels validated before any action.

## Install

```bash
pipx install .
# or
uvx pip install .
```

Python 3.11+, stdlib-only at runtime.

## Agent integration

- **Claude Code** — `slopsweep hooks print --for claude-code` (SessionStart/SessionEnd hooks; verify against [Claude Code hooks docs](https://code.claude.com/docs/en/hooks)).
- **Codex / shell** — `slopsweep hooks print --for codex`
- **Skill** — copy `skills/slopsweep/SKILL.md` into your agent skills folder.
- **Cron safety net** — `slopsweep hooks print --for cron`

slopsweep **prints** snippets; it never edits your agent config.

## Limitations (v0.1)

- Linux and macOS are first-class; Windows is best-effort.
- No GUI, no cloud sync, no auto-editing of agent settings.
- Triage is manual: you run an LLM with [docs/triage-prompt.md](docs/triage-prompt.md).
- PyPI publish pending name confirmation—build wheels locally.

## Prior art

| Project | Focus |
|---------|--------|
| [p3nchan/auto-optimization](https://github.com/p3nchan/auto-optimization) | Tiered shell scripts for agent workspace hygiene |
| [tianrking/ClawRemove](https://github.com/tianrking/ClawRemove) | Go binary auditing agent runtimes and caches |

**slopsweep** differentiators: session-scoped `tmp/`/`outputs/`, per-session manifest, agent-agnostic rules block, trash-then-purge with verified archives, and metadata-only LLM triage with validated labels.

## License

MIT — see [LICENSE](LICENSE).
