# slopsweep: build brief for the coding agent

Read this whole file before writing code. Save it as `AGENTS.md` (or `CLAUDE.md`) in the repo root and follow it for the whole build.

## 1. Mission

Build **slopsweep**, an open-source tool that stops AI coding agents from bloating disk with junk files, and reclaims the space they already used.

Core idea: **prevent junk with a session directory layout, clean it with deterministic code (zero LLM tokens), and use an LLM only to label the few ambiguous leftovers, from metadata only.** Anything the LLM says is validated before it touches a file.

Working name is `slopsweep`. Before any PyPI publish, check that the name is free on GitHub, PyPI, and npm. Keep the name in one constant so it can be renamed.

### Prior art (differentiate, don't copy)
`p3nchan/auto-optimization` (tiered shell scripts for agent workspace hygiene) and `tianrking/ClawRemove` (Go binary that audits and cleans agent runtimes and caches) are the closest projects. Read their READMEs for positioning only. Do not copy code. Our differentiators: session-scoped scratch/outputs layout, per-session manifest, agent-agnostic rules block, trash-then-purge and verified archiving, and metadata-only LLM triage with validated labels.

## 2. Non-negotiable safety rules

This tool deletes files. Safety beats features.

1. **Dry-run is the default.** Nothing changes without `--apply`.
2. **Delete = move to trash first**, purged only after `trash_ttl_days`.
3. **Outputs are never deleted directly.** They are archived (verified) or left alone.
4. **Containment:** resolve every path with `os.path.realpath`. Refuse any path that is not strictly inside the configured root. Never follow symlinks (use `lstat`; treat symlinks as leaf entries, and never traverse into them or archive their targets).
5. **Root guard:** refuse to run unless the root contains a `.slopsweep-root` marker file created by `init`. Refuse if root is `/`, `$HOME`, or a filesystem root.
6. **Skip anything git-tracked or inside a git work tree** (`.git` present in any ancestor within the root).
7. **No shell parsing.** Use `pathlib`/`os` only; never build shell command strings. Filenames may contain spaces, newlines, or unicode.
8. **Single-run lock:** use a lockfile in the root so concurrent runs cannot overlap.
9. **Archive verification:** after writing an archive, re-open and list it; only then remove originals. On failure, keep originals and delete the partial archive.
10. **LLM labels are untrusted input.** Validate: path exists, is inside root, not a symlink, not git-tracked, label in `{keep, archive, delete}`. Reject the whole file if it is malformed. `delete` still goes to trash.
11. **Secrets:** triage must never include content from files matching secret patterns (`.env*`, `*.pem`, `*.key`, `id_rsa*`, `*credentials*`, `*.p12`, `*.pfx`, `*secret*`). Metadata only for those.
12. Never touch the network. No telemetry.

## 3. Tech and conventions

- **Python 3.11+, standard library only** at runtime (`tomllib` for config). Dev deps allowed: `pytest`, `ruff`, `mypy`.
- `src/` layout, `pyproject.toml` (PEP 621), entry point `slopsweep`.
- Type hints everywhere; `mypy --strict` on `src/`.
- Cross-platform: Linux and macOS first-class. Windows: best effort, document limits.
- Small pure functions. Separate **planning** (compute a list of actions) from **execution** (apply actions). Dry-run prints the plan; apply executes the same plan.
- Time is injectable (`now` parameter) so tests never sleep.
- Logs: human summary to stdout; JSONL audit log at `<root>/logs/slopsweep.jsonl`, one line per action (timestamp UTC, action, path, bytes, dry_run).

## 4. Layout the tool manages

```
<root>/                      # default ~/agent-work, must contain .slopsweep-root
  sessions/<session-id>/
    tmp/                     # scratch: disposable
    outputs/                 # deliverables: archived, never silently deleted
    manifest.jsonl           # one JSON object per line: path, purpose, verdict(keep|discard), ts
    .session.json            # started_at, ended_at (null while active)
  .trash/<YYYY-MM-DD>/       # moved-here items
  archive/<session-id>.tar.gz
  logs/slopsweep.jsonl
  triage.jsonl               # generated on demand
```

Config: `~/.config/slopsweep/config.toml`, overridable by env vars and flags. Defaults: `scratch_ttl_hours=24`, `trash_ttl_days=7`, `archive_after_days=30`, `triage_peek_bytes=200`.

## 5. CLI spec

```
slopsweep init [--root PATH]            create layout, marker file, default config
slopsweep session new [--id ID]         create session dirs; print shell exports (SLOPSWEEP_SESSION, TMPDIR)
slopsweep session end [--id ID]         mark ended (makes scratch eligible immediately)
slopsweep manifest add PATH --purpose TEXT --verdict keep|discard    atomic append, agent-friendly
slopsweep run [--apply] [--json]        phases below; dry-run by default
slopsweep triage [--out FILE]           write metadata JSONL for ambiguous entries
slopsweep apply-labels FILE [--apply]   validate then apply LLM labels
slopsweep status                        sizes per session, trash, archive; estimated reclaimable
slopsweep rules                         print the agent rules block (from packaged data)
slopsweep hooks print --for claude-code|codex|cron    print hook/cron snippets, never edit user config
```

Exit codes: `0` ok, `1` error, `2` usage, `3` refused by a safety rule.

### `run` phases (in order)
1. **Manifest discards:** move entries marked `discard` to trash.
2. **Stale scratch:** a session's `tmp/` is eligible if the session has ended, or no file inside was modified within `scratch_ttl_hours`. Move to trash.
3. **Old outputs:** if every file in `outputs/` is older than `archive_after_days`, write a verified tar.gz (stdlib `tarfile`, no symlink following), then remove originals.
4. **Purge trash** older than `trash_ttl_days`.

"Ambiguous" = anything in a session root that is not `tmp/`, `outputs/`, `manifest.jsonl`, or `.session.json`. Phase 5 (`triage`) handles those.

## 6. Triage format

`triage.jsonl`, one object per ambiguous entry: `{path, kind, size_bytes, mtime, peek}` where `peek` is the first `triage_peek_bytes` of text (empty for binaries and secret-pattern files). Labels file returned by the LLM is JSONL: `{path, label}`. Provide `docs/triage-prompt.md` with a ready prompt that tells the model to return only that JSONL.

## 7. Repo layout

```
src/slopsweep/          core (plan.py, execute.py, safety.py, config.py, cli.py, triage.py, manifest.py)
tests/
skills/slopsweep/SKILL.md      canonical skill (YAML frontmatter: name, description) for manual sweep + triage
rules/AGENT_RULES.md           the always-on rules block (Appendix A)
hooks/                          example snippets (printed by `hooks print`)
docs/                           triage-prompt.md, safety-model.md
README.md  LICENSE (MIT)  SECURITY.md  CONTRIBUTING.md  CHANGELOG.md  .github/workflows/ci.yml
```

Skill and rules must ship inside the package as package data so `slopsweep rules` works after `pipx install`.

For hooks, verify current syntax against the agent's official docs before writing examples (Claude Code SessionStart/SessionEnd hooks in settings.json; cron for the nightly safety net). Do not invent config keys.

## 8. Tests (required before v0.1)

Use `tmp_path` fixtures and an injected clock. Must cover:
- dry-run changes nothing (snapshot the tree before and after)
- scratch TTL boundary, ended-session shortcut, recently modified file blocks eviction
- manifest discard, malformed manifest lines, missing files
- archive verify failure keeps originals
- symlink escape: a symlink in `tmp/` pointing outside root is never followed or deleted-through
- git-tracked dir skipped
- filenames with spaces, newlines, unicode
- root guard refuses `/`, `$HOME`, and dirs without the marker
- lockfile prevents a second concurrent run
- labels validation: outside-root path, symlink, bad label, malformed JSONL (whole file rejected)
- triage never emits content for secret-pattern files
- trash purge boundary

## 9. Milestones (stop and report after each; commit small)

- **M0 Scaffold:** pyproject, src layout, CLI skeleton, ruff/mypy/pytest wired, CI on Linux and macOS for Python 3.11 to 3.13.
- **M1 Safety core:** `safety.py` (containment, symlink, git, root guard, lock) with full tests before any deletion code exists.
- **M2 Engine:** planner + executor, phases 1 to 4, JSONL audit log, `run`, `status`.
- **M3 Session and manifest commands:** `init`, `session`, `manifest add`.
- **M4 Triage:** `triage`, `apply-labels`, triage prompt doc.
- **M5 Adapters:** SKILL.md, rules block, `rules` and `hooks print`.
- **M6 Release:** README (see below), SECURITY.md, CONTRIBUTING.md, CHANGELOG, LICENSE, tag `v0.1.0`, build wheel and sdist, do not publish to PyPI until the owner confirms the name.

### README must include
One-line pitch, the problem, a before/after disk-space example, 60-second quickstart, the safety model, the three-layer design (rules, deterministic cleanup, LLM triage), install (`pipx`/`uvx`), how to add the skill for Claude Code and Codex, honest limitations, and the prior-art comparison.

## 10. How you work

- Follow this brief; if something is ambiguous, pick the safer option and note it in the PR/commit message.
- **Do not create slop yourself:** no summary or notes files, no `_v2` copies, scratch only in a temp dir you delete. Commit only what the project needs.
- Add no runtime dependencies. Ask before adding any dev dependency beyond the three listed.
- Run `ruff`, `mypy`, and `pytest` before every commit; never commit failing tests.
- Out of scope for v0.1: GUI, network features, Windows polish, auto-editing user agent configs, cloud sync.

---

## Appendix A: `rules/AGENT_RULES.md` (ship this text)

```
## File hygiene (storage rules)

Your session directory is `$SLOPSWEEP_ROOT/sessions/$SLOPSWEEP_SESSION/`.

1. Scratch goes in `tmp/` only (TMPDIR points there). It is deleted automatically.
2. Deliverables go in `outputs/` only, and only when the user asked for a file. Reply inline otherwise.
3. Do not create summary, notes, report, changelog, or explanation files unless asked.
4. Overwrite, don't multiply: never create _v2, _final, _new, _backup, or copy variants.
5. Log every file you create outside tmp/ with:
   slopsweep manifest add <path> --purpose "<why>" --verdict keep|discard
   Mark discard on anything that turned out not to be needed.
6. Delete what you created and no longer need before finishing, especially large generated data, screenshots, and build artifacts.
7. If one file would exceed 50 MB or a task would create over 100 files, stop and ask first.
8. Never touch files outside your session directory. Never delete anything git-tracked.
```
