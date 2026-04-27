"""Visualization utilities for HAEO scenario test results."""

from __future__ import annotations

from collections.abc import Mapping
import json
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.topology import serialize_topology

from .graph import create_graph_visualization

_LOGGER = logging.getLogger(__name__)

CARD_WIDTH = 1920
CARD_HEIGHT = 900


def create_card_visualization(
    output_sensors: Mapping[str, Mapping[str, Any]],
    output_path: str,
) -> None:
    """Render the HAEO forecast card as SVG via the bundled card component.

    Calls the Node.js export script which uses JSDOM to render the card
    headlessly.

    Raises:
        RuntimeError: If the export script is missing, Node.js is not
            installed, or the card fails to render.

    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    script = repo_root / "frontend" / "haeo-forecast-card" / "scripts" / "export-scenario-svg.mjs"

    if not script.exists():
        msg = f"Card export script not found: {script}"
        raise RuntimeError(msg)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(output_sensors, f, default=str)
        temp_path = f.name

    try:
        result = subprocess.run(  # noqa: S603 — trusted repo-local script, no user input
            ["node", str(script), temp_path, output_path],  # noqa: S607 — node is a well-known executable
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(script.parent.parent),
            check=False,
        )
        if result.returncode != 0:
            msg = f"Card export failed (exit {result.returncode}): {result.stderr}"
            raise RuntimeError(msg)
    except FileNotFoundError as e:
        msg = f"Node.js not found — required for card visualization: {e}"
        raise RuntimeError(msg) from e
    except subprocess.TimeoutExpired as e:
        msg = f"Card export timed out after {e.timeout}s"
        raise RuntimeError(msg) from e
    finally:
        Path(temp_path).unlink(missing_ok=True)


def visualize_scenario_results(
    output_sensors: Mapping[str, Mapping[str, Any]],
    scenario_name: str,
    output_dir: Path,
    network: Network,
) -> None:
    """Create visualizations for HAEO scenario test results.

    Renders the forecast card as the main optimization chart and creates
    a network topology graph.

    Args:
        output_sensors: Dict mapping entity_id to sensor state dict.
        scenario_name: Name identifier for the scenario (used in filenames).
        output_dir: Directory path where visualization files will be saved.
        network: Network object for graph visualization.

    """
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    main_plot_path = output_dir_path / f"{scenario_name}_optimization.svg"
    create_card_visualization(output_sensors, str(main_plot_path))

    graph_plot_path = output_dir_path / f"{scenario_name}_network_topology.svg"
    create_graph_visualization(network, str(graph_plot_path), f"{scenario_name.title()} Network Topology")


    topology_path = output_dir_path / f"{scenario_name}_topology.json"
    topology_data = serialize_topology(network)
    with topology_path.open("w") as f:
        json.dump(topology_data, f, indent=2)
        f.write("\n")
