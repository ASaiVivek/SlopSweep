# Security

slopsweep deletes and archives files. Treat it like any destructive maintenance tool.

## Reporting

If you find a safety bug (path escape, symlink follow, bypass of dry-run, etc.), open a private security advisory on GitHub or email the maintainers listed in the repository.

## Threat model

- **Local operator** runs slopsweep against a marked workspace root.
- **LLM labels** are untrusted; `apply-labels` validates paths and rejects malformed JSONL.
- **No network** at runtime; no telemetry.

## Recommendations

- Always run `slopsweep run` (dry-run) before `--apply`.
- Keep the workspace root off `$HOME` and filesystem roots.
- Do not point slopsweep at production data directories.
