"""Pytest fixtures for model tests."""

from highspy import Highs
import pytest


@pytest.fixture
def solver() -> Highs:
    """Provide a HiGHS solver instance for testing.

    The solver is configured to suppress console output.
    """
    h = Highs()
    h.setOptionValue("output_flag", False)  # noqa: FBT003
    h.setOptionValue("log_to_console", False)  # noqa: FBT003
    return h
