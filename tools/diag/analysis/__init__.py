"""Analysis modules for the diagnostics CLI.

Each module answers one specific question about a plan the optimizer produced,
and renders the answer as text a human or an agent can read directly. They are
selected with `diag --analysis <name>` and listed with `--list-analyses`.

Analyses read the diagnostics export rather than a re-solved network, so they
describe the plan that actually ran and work with `--outputs-only`.

Adding one:

1. Create a module here defining `NAME`, `HELP`, and
   `run(outputs, config, argument) -> str`.
2. Import it below and add it to `ANALYSES`.
3. Add a case to `tests/test_diag_analysis.py`.

Keep the output readable rather than machine-parseable: the caller is trying to
understand a decision, so lead with the finding and show the numbers supporting
it.
"""

from collections.abc import Mapping
from typing import Any, Final, Protocol

from . import binding, series


class Analysis(Protocol):
    """Renders one answer about a diagnostics export."""

    NAME: str
    HELP: str

    def run(self, outputs: Mapping[str, Any], config: Mapping[str, Any], argument: str) -> str:
        """Return the analysis output as readable text."""
        ...


ANALYSES: Final[dict[str, Any]] = {
    binding.NAME: binding,
    series.NAME: series,
}


def describe_analyses() -> str:
    """Return a listing of the available analyses."""
    width = max(len(name) for name in ANALYSES)
    lines = [f"  {name:<{width}}  {module.HELP}" for name, module in sorted(ANALYSES.items())]
    return "Available analyses:\n" + "\n".join(lines)


def run_analysis(spec: str, outputs: Mapping[str, Any], config: Mapping[str, Any]) -> str:
    """Run one `name` or `name:argument` spec against a diagnostics export."""
    name, _, argument = spec.partition(":")
    module = ANALYSES.get(name)
    if module is None:
        known = ", ".join(sorted(ANALYSES))
        msg = f"unknown analysis {name!r}; available: {known}"
        raise KeyError(msg)
    return module.run(outputs, config, argument)
