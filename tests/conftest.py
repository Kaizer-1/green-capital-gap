"""Shared fixtures."""

from __future__ import annotations

import pytest

from gcg.config import load_config


@pytest.fixture(scope="session")
def cfg():
    """The real project configuration.

    The classifier tests run against the production lexicon on purpose. A test
    that passes against a toy lexicon proves nothing about the lexicon that
    actually labels the data.
    """
    return load_config()
