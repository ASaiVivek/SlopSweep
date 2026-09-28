# Triage prompt (metadata only)

You are labeling ambiguous files in an agent workspace. You will receive JSONL metadata (`path`, `kind`, `size_bytes`, `mtime`, `peek`). **Do not request or assume file contents beyond `peek`.**

Return **only** JSONL, one object per line:

```json
{"path": "sessions/abc/notes.txt", "label": "delete"}
```

Labels must be exactly one of: `keep`, `archive`, `delete`.

- `keep` — leave the file in place.
- `archive` — verified archive (for deliverables or worth keeping off-disk).
- `delete` — move to trash (recoverable until trash TTL).

Prefer `delete` for summaries, scratch copies, and duplicate reports. Prefer `archive` for user-requested deliverables in the wrong folder. Use `keep` when unsure.

Do not include markdown fences or commentary.
