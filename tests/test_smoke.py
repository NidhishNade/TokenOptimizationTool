"""A tiny 'smoke test' to prove the project + pytest are wired up correctly."""

from optimizer import __version__


def test_package_imports():
    """The package should import and expose a version string."""
    assert isinstance(__version__, str)
    assert __version__ != ""
