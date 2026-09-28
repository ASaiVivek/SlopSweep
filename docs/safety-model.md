# Safety model

slopsweep deletes or archives files. Defaults are conservative.

| Rule | Behavior |
|------|----------|
| Dry-run default | `run` and `apply-labels` plan only unless `--apply` |
| Trash first | Deletes move to `.trash/<date>/` before purge |
| Outputs | Session `outputs/` are archived (verified tar.gz), not silently deleted |
| Containment | `realpath` checks; symlinks are leaves, never followed |
| Root guard | Requires `.slopsweep-root`; refuses `/` and `$HOME` |
| Git | Skips paths inside a `.git` work tree under the root |
| Lock | `.slopsweep.lock` prevents overlapping runs |
| LLM labels | Parsed as untrusted; invalid files rejected wholesale |
| Secrets | Triage omits `peek` for secret-like filenames |

See `AGENTS.md` section 2 for the authoritative list.
