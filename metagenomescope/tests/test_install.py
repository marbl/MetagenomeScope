import importlib
from metagenomescope import __version__, __name__


def test_version_consistent():
    # Checks that the version we set in __init__.py matches the
    # version that was set when installing MetagenomeScope. I'm
    # adding this test as recommended by
    # https://packaging.python.org/en/latest/discussions/single-source-version/
    assert __version__ == importlib.metadata.version(__name__)
