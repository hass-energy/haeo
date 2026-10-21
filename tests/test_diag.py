"""Regression tests for the `uv run diag` CLI.

diag assembles its own network instead of going through the coordinator, so it
has to repeat every step the coordinator performs before adding elements. That
is easy to leave out of sync, and it silently was: diag omitted
`compile_policies()`, so every re-solve failed on connections missing their
tags. These tests run the real optimization path over committed scenarios, so
the next step that goes missing fails here rather than the next time someone
debugs a user report.
"""

import json
from pathlib import Path
import shutil

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


@pytest.mark.timeout(60)
@pytest.mark.parametrize(
    ("relax_infeasible", "expected"),
    [
        pytest.param(False, "Optimization failed with status: Infeasible (conflicting constraints:", id="infeasible"),
        pytest.param(True, "Relaxed Switchboard element_power_balance[0] by", id="relaxed"),
    ],
)
def test_diag_follows_the_hub_relax_setting(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], *, relax_infeasible: bool, expected: str
) -> None:
    """A load no source can supply fails with its conflicts, or is relaxed when the hub relaxes impossible plans."""
    for name in ("environment.json", "inputs.json"):
        shutil.copy(SCENARIOS_DIR / "scenario1" / name, tmp_path / name)
    config = json.loads((SCENARIOS_DIR / "scenario1" / "config.json").read_text())
    config["participants"]["Constant Load"]["forecast"]["forecast"]["value"] = 500.0
    config["advanced"] = {"relax_infeasible": relax_infeasible}
    (tmp_path / "config.json").write_text(json.dumps(config))

    if relax_infeasible:
        run_diagnostics(tmp_path)
    else:
        with pytest.raises(SystemExit):
            run_diagnostics(tmp_path)

    assert expected in capsys.readouterr().out
