"""Regression tests for the `uv run diag` CLI.

diag assembles its own network instead of going through the coordinator, so it
has to repeat every step the coordinator performs before adding elements. That
is easy to leave out of sync, and it silently was: diag omitted
`compile_policies()`, so every re-solve failed on connections missing their
tags. These tests run the real optimization path over committed scenarios, so
the next step that goes missing fails here rather than the next time someone
debugs a user report.
"""

from pathlib import Path

import pytest

from tools.diag import run_diagnostics

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

# One scenario without a policy element and one with, so both the plain tagging
# path and the policy pricing compilation path are exercised.
SCENARIOS = ["scenario1", "scenario6"]


@pytest.mark.timeout(60)
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_diag_runs_optimization(scenario: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Diag reruns the optimization and prints a result table."""
    run_diagnostics(SCENARIOS_DIR / scenario)

    output = capsys.readouterr().out
    assert "Optimization complete" in output
    assert "Battery" in output


@pytest.mark.timeout(60)
def test_diag_compare_against_stored_outputs(capsys: pytest.CaptureFixture[str]) -> None:
    """Diag compares stored diagnostics outputs against a fresh optimization."""
    run_diagnostics(SCENARIOS_DIR / "scenario1", compare=True)

    assert "Optimization complete" in capsys.readouterr().out


def test_diag_outputs_only_skips_optimization(capsys: pytest.CaptureFixture[str]) -> None:
    """Outputs-only mode reads the stored table without building a network."""
    run_diagnostics(SCENARIOS_DIR / "scenario1", outputs_only=True)

    output = capsys.readouterr().out
    assert "Optimization complete" not in output
    assert "Battery" in output
