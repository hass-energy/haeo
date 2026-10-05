"""HAEO diagnostics CLI.

`diag` answers questions about a plan the optimizer produced: what it decided,
and why. The default run re-solves a diagnostics export and prints the plan;
analysis modules under `analysis/` answer narrower questions about it.
"""

from .cli import DiagnosticsData as DiagnosticsData
from .cli import main as main
from .cli import run_diagnostics as run_diagnostics
