# Contributing

Thanks for helping improve slopsweep.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python3 -m ruff check src tests
python3 -m mypy src
python3 -m pytest
```

## Guidelines

- Prefer the **safer** behavior when requirements are ambiguous.
- No runtime dependencies beyond the Python stdlib.
- Run ruff, mypy (`--strict` on `src/`), and pytest before every commit.
- Do not add summary/scratch files to the repo; keep the tree minimal.

## Pull requests

- Describe safety implications for any change that touches deletion, archives, or path resolution.
- Add tests for new behavior using `tmp_path` and an injectable clock.
