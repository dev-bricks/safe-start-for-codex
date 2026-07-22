"""Safe Start for Codex."""

__all__ = ["__version__"]

# `pyproject.toml` is the release-version authority. Keep this import-safe
# source marker in sync; tests/test_version_metadata.py guards the contract.
__version__ = "1.1.3"
