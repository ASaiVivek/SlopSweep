from slopsweep import TOOL_NAME, __version__


def test_constants() -> None:
    assert TOOL_NAME == "slopsweep"
    assert __version__ == "0.1.0"
