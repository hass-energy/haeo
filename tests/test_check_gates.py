"""Tests that CI and the gate runner cannot drift apart.

`tools/check.py` is the single definition of what each gate runs, and
`.github/workflows/ci.yml` is expected to invoke it rather than repeat the
commands. These tests fail if a gate is added to one and not the other, which is
the failure mode the shared script exists to prevent.
"""

import os
from pathlib import Path
import re
from typing import TypedDict

import pytest
import yaml

from tools.check import GATES, GATES_BY_NAME, bundle_is_stale, selected_gates

WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"

# Jobs that legitimately do not invoke the runner: they are wholly provided by a
# third-party action, or they aggregate other jobs.
ACTION_ONLY_JOBS = {"hassfest", "hacs", "ci-passed"}


class WorkflowStep(TypedDict, total=False):
    """The part of a CI workflow step these tests read."""

    run: str


class WorkflowJob(TypedDict, total=False):
    """The parts of a CI workflow job these tests read."""

    steps: list[WorkflowStep]
    needs: list[str]


class Workflow(TypedDict):
    """The part of the CI workflow these tests read."""

    jobs: dict[str, WorkflowJob]


def workflow() -> Workflow:
    """Return the parsed CI workflow."""
    parsed: Workflow = yaml.safe_load(WORKFLOW.read_text())
    return parsed


def gate_invocations() -> dict[str, str]:
    """Return {gate name: job name} for every gate CI runs through the script."""
    found: dict[str, str] = {}
    for job_name, job in workflow()["jobs"].items():
        for step in job.get("steps", []):
            run = step.get("run", "")
            for match in re.finditer(r"tools/check\.py\s+([a-z-]+)", run):
                found[match.group(1)] = job_name
    return found


def test_every_ci_invocation_names_a_real_gate() -> None:
    """CI cannot invoke a gate the runner does not define."""
    unknown = {gate: job for gate, job in gate_invocations().items() if gate not in GATES_BY_NAME}

    assert not unknown, f"CI invokes gates that tools/check.py does not define: {unknown}"


def test_every_default_gate_runs_in_ci() -> None:
    """A gate that runs locally by default must also be enforced by CI."""
    invoked = set(gate_invocations())
    expected = {gate.name for gate in GATES if gate.default and gate.runs_locally}

    assert expected <= invoked, f"gates missing from CI: {sorted(expected - invoked)}"


def test_action_only_gates_are_not_invoked_through_the_script() -> None:
    """Gates with no local command must not pretend to run through the runner."""
    invoked = set(gate_invocations())
    action_only = {gate.name for gate in GATES if not gate.runs_locally}

    assert not (action_only & invoked), f"action-only gates invoked as commands: {sorted(action_only & invoked)}"


def test_action_only_gates_have_a_corresponding_ci_job() -> None:
    """Gates the runner cannot run must still be covered by a CI job."""
    jobs = set(workflow()["jobs"])

    for gate in GATES:
        if not gate.runs_locally:
            assert gate.name in jobs, f"{gate.name} has no local command and no CI job"


def test_gates_without_a_command_explain_why() -> None:
    """A gate the runner skips must say what covers it instead."""
    for gate in GATES:
        if not gate.runs_locally or not gate.default:
            assert gate.reason, f"{gate.name} is skipped locally but gives no reason"


def test_required_check_depends_on_every_gate_job() -> None:
    """The single required check must aggregate each gate's job."""
    jobs = workflow()["jobs"]
    needs = set(jobs["ci-passed"].get("needs", []))
    gate_jobs = {job for job in jobs if job not in ACTION_ONLY_JOBS} | {"hassfest", "hacs"}

    assert gate_jobs <= needs, f"jobs missing from the CI passed check: {sorted(gate_jobs - needs)}"


def test_default_selection_excludes_gates_that_cannot_run_locally() -> None:
    """Running with no arguments must not try to execute action-only gates."""
    for gate in selected_gates([], fast=False):
        assert gate.runs_locally


@pytest.mark.parametrize("name", [gate.name for gate in GATES])
def test_gate_names_are_selectable(name: str) -> None:
    """Every gate can be selected by its exact name."""
    assert [gate.name for gate in selected_gates([name], fast=False)] == [name]


def test_unknown_gate_selection_lists_the_alternatives() -> None:
    """A typo names what was available rather than failing opaquely."""
    with pytest.raises(SystemExit, match="unknown gate 'nope'"):
        selected_gates(["nope"], fast=False)


def test_bundle_is_stale_when_missing(tmp_path: Path) -> None:
    """A bundle that was never built must be built."""
    source = tmp_path / "src" / "card.ts"
    source.parent.mkdir()
    source.write_text("")

    assert bundle_is_stale(tmp_path / "dist" / "bundle.mjs", [tmp_path / "src"])


@pytest.mark.parametrize(
    ("source_age", "expected"),
    [pytest.param(-10, False, id="sources_older"), pytest.param(10, True, id="source_newer")],
)
def test_bundle_is_stale_compares_against_sources(tmp_path: Path, source_age: int, expected: bool) -> None:
    """A bundle is rebuilt only when a file it is built from changed after it, including nested and single files."""
    bundle = tmp_path / "dist" / "bundle.mjs"
    bundle.parent.mkdir()
    bundle.write_text("")
    nested = tmp_path / "src" / "topology" / "layout.ts"
    nested.parent.mkdir(parents=True)
    nested.write_text("")
    config = tmp_path / "package.json"
    config.write_text("")
    built = bundle.stat().st_mtime
    os.utime(config, (built - 10, built - 10))
    os.utime(nested, (built + source_age, built + source_age))

    assert bundle_is_stale(bundle, [tmp_path / "src", config]) is expected
