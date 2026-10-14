"""Pytest fixtures for model tests."""

import pytest

from custom_components.haeo.core.model.solver import Solver


@pytest.fixture
def solver() -> Solver:
    """Provide a HiGHS solver instance for testing.

    The solver is configured to suppress console output.
    """
    h = Solver()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("log_to_console", False)
    return h
