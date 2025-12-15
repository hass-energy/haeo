"""Graph visualization for HAEO network topology.

This module creates network topology diagrams showing model elements and connections
with grouping by their parent device elements. Uses the adapter layer to extract
model elements from device configurations.
"""

from collections import defaultdict
import logging
from pathlib import Path
from typing import Any

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx

from custom_components.haeo.elements import ELEMENT_TYPES

_LOGGER = logging.getLogger(__name__)

# Model element type for connections (from model layer)
MODEL_ELEMENT_TYPE_CONNECTION = "connection"


def _extract_model_elements(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Extract model elements from device configurations.

    Returns:
        Tuple of (model_elements, element_to_device_map) where:
        - model_elements: List of all model elements created by all device elements
        - element_to_device_map: Maps model element names to their parent device names

    """
    participants = config.get("participants", {})

    all_model_elements: list[dict[str, Any]] = []
    element_to_device: dict[str, str] = {}

    for device_name, device_config in participants.items():
        element_type = device_config.get("element_type", "")

        if element_type not in ELEMENT_TYPES:
            _LOGGER.warning("Unknown element type: %s", element_type)
            continue

        # Convert config to loaded format (use constant values for sensors)
        loaded_config = _config_to_loaded(device_config)

        # Get model elements from the adapter
        model_elements = ELEMENT_TYPES[element_type].create_model_elements(loaded_config)

        for model_element in model_elements:
            all_model_elements.append(model_element)
            element_to_device[model_element["name"]] = device_name

    return all_model_elements, element_to_device


def _config_to_loaded(config: dict[str, Any]) -> dict[str, Any]:
    """Convert a config dict to a loaded data format.

    For visualization purposes, we replace sensor references with empty lists
    since we only need the structure, not actual sensor values.
    """
    loaded: dict[str, Any] = {}

    for key, value in config.items():
        if isinstance(value, str) and value.startswith("sensor."):
            # Single sensor reference - use empty list as placeholder
            loaded[key] = [0.0]
        elif isinstance(value, list):
            # List of values or sensors - preserve or convert to placeholder
            is_sensors = all(isinstance(v, str) and v.startswith("sensor.") for v in value)
            is_input_numbers = all(isinstance(v, str) and v.startswith("input_number.") for v in value)
            if is_sensors or is_input_numbers:
                loaded[key] = [0.0]
            else:
                loaded[key] = value
        else:
            loaded[key] = value

    return loaded


def create_graph_visualization(
    config: dict[str, Any],
    output_path: str,
    title: str,
    *,
    generate_png: bool = True,
) -> None:
    """Create a graph visualization of the network topology using model elements.

    Extracts model elements from device configurations using the adapter layer,
    and displays them grouped by their parent device element.
    """
    # Extract model elements and their parent device mapping
    model_elements, element_to_device = _extract_model_elements(config)

    # Create directed graph
    graph: nx.DiGraph[str] = nx.DiGraph()

    # Color map for model element types
    model_color_map = {
        "battery": "#98df8a",  # Light green
        "source_sink": "#aec7e8",  # Light blue
        "node": "#f0f0f0",  # Very light gray
    }

    # Color map for device element types (for grouping)
    device_color_map = {
        "battery": "#c5e8b7",  # Lighter green
        "photovoltaics": "#ffe4c4",  # Lighter orange
        "grid": "#d4e5f7",  # Lighter blue
        "load": "#e8e8e8",  # Light gray
        "node": "#f8f8f8",  # Very light gray
        "connection": "#f0e6ff",  # Light purple
    }

    # Get device types for coloring groups
    participants = config.get("participants", {})
    device_types: dict[str, str] = {name: cfg.get("element_type", "") for name, cfg in participants.items()}

    # First pass: add all non-connection model elements as nodes
    for model_element in model_elements:
        model_type = model_element.get("element_type", "")
        name = model_element["name"]

        if model_type != MODEL_ELEMENT_TYPE_CONNECTION:
            fillcolor = model_color_map.get(model_type, "lightgray")
            parent_device = element_to_device.get(name, "")
            graph.add_node(
                name,
                color=fillcolor,
                model_type=model_type,
                parent_device=parent_device,
            )

    # Second pass: add connections as edges
    for model_element in model_elements:
        model_type = model_element.get("element_type", "")

        if model_type == MODEL_ELEMENT_TYPE_CONNECTION:
            source = model_element.get("source", "")
            target = model_element.get("target", "")
            connection_name = model_element["name"]
            parent_device = element_to_device.get(connection_name, "")

            if source and target and source in graph.nodes() and target in graph.nodes():
                graph.add_edge(
                    source,
                    target,
                    name=connection_name,
                    parent_device=parent_device,
                )

    if len(graph.nodes()) == 0:
        _LOGGER.warning("No nodes to visualize")
        return

    # Use spring layout for better visualization of grouped elements
    pos = nx.spring_layout(graph, seed=42, k=2.0)  # type: ignore[no-untyped-call]

    # Group nodes by parent device for drawing bounding boxes
    device_groups: dict[str, list[str]] = defaultdict(list)
    for node in graph.nodes():
        parent = graph.nodes[node].get("parent_device", "")
        if parent:
            device_groups[parent].append(node)

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_title(title, fontsize=14, pad=20)

    # Draw bounding boxes for device groups
    for device_name, nodes in device_groups.items():
        if len(nodes) < 1:
            continue

        # Get positions of all nodes in this group
        node_positions = [pos[node] for node in nodes]
        xs = [p[0] for p in node_positions]
        ys = [p[1] for p in node_positions]

        # Calculate bounding box with padding
        padding = 0.15
        min_x, max_x = min(xs) - padding, max(xs) + padding
        min_y, max_y = min(ys) - padding, max(ys) + padding

        # Get device type for coloring
        device_type = device_types.get(device_name, "")
        group_color = device_color_map.get(device_type, "#f0f0f0")

        # Draw rounded rectangle for the group
        rect = mpatches.FancyBboxPatch(
            (min_x, min_y),
            max_x - min_x,
            max_y - min_y,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor=group_color,
            edgecolor="#999999",
            linewidth=1.5,
            alpha=0.5,
            zorder=0,
        )
        ax.add_patch(rect)

        # Add device label above the group
        label_y = max_y + 0.02
        ax.text(
            (min_x + max_x) / 2,
            label_y,
            f"{device_name}\n({device_type})",
            fontsize=9,
            fontweight="bold",
            ha="center",
            va="bottom",
            color="#333333",
        )

    # Draw nodes with type-specific colors
    for node in graph.nodes():
        node_color = graph.nodes[node].get("color", "lightgray")
        model_type = graph.nodes[node].get("model_type", "")

        nx.draw_networkx_nodes(  # type: ignore[no-untyped-call]
            graph,
            pos,
            nodelist=[node],
            node_color=node_color,
            node_size=2000,
            node_shape="o",
            edgecolors="black",
            linewidths=1.5,
            ax=ax,
        )

        # Draw node label with model element name (abbreviated) and type
        # Abbreviate long names by taking the part after the last ':'
        display_name = node.split(":")[-1] if ":" in node else node
        label_text = f"{display_name}\n({model_type})"
        nx.draw_networkx_labels(  # type: ignore[no-untyped-call]
            graph, pos, labels={node: label_text}, font_size=8, font_family="sans-serif", ax=ax
        )

    # Draw edges with arrows
    nx.draw_networkx_edges(  # type: ignore[no-untyped-call]
        graph,
        pos,
        edge_color="#666666",
        arrows=True,
        arrowsize=20,
        arrowstyle="->",
        width=2.0,
        node_size=2000,
        min_source_margin=15,
        min_target_margin=15,
        ax=ax,
        connectionstyle="arc3,rad=0.1",
    )

    # Draw edge labels showing connection names
    edge_labels = {(u, v): data.get("name", "").split(":")[-1] for u, v, data in graph.edges(data=True)}
    nx.draw_networkx_edge_labels(  # type: ignore[no-untyped-call]
        graph,
        pos,
        edge_labels=edge_labels,
        font_size=7,
        bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": "none", "alpha": 0.8},
        font_color="#333333",
        ax=ax,
    )

    # Remove axis
    ax.axis("off")
    plt.tight_layout()

    # Save the graph
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as SVG
    plt.savefig(output_path, format="svg", bbox_inches="tight", dpi=300)
    _LOGGER.info("Graph visualization saved to %s", output_path)

    # Optionally save as PNG
    if generate_png:
        png_path = str(output_path).replace(".svg", ".png")
        plt.savefig(png_path, format="png", bbox_inches="tight", dpi=300)
        _LOGGER.info("Graph visualization saved to %s", png_path)

    plt.close(fig)
