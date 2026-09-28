from __future__ import annotations

import pytest

from slopsweep.manifest import parse_manifest_lines


def test_malformed_manifest_line() -> None:
    with pytest.raises(ValueError):
        parse_manifest_lines("{not json")


def test_missing_verdict() -> None:
    with pytest.raises(ValueError):
        parse_manifest_lines('{"path": "a", "purpose": "p"}')
