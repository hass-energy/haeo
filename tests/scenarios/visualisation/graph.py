"""Graph visualization for HAEO network topology.

This module creates network topology diagrams showing model elements and their
connections as created by the adapter layer. Uses the Network object to extract
the actual model elements after optimization, grouped by parent device.
"""

from collections import defaultdict
import logging
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx

from custom_components.haeo.model import Network
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.elements import Battery, BatteryBalanceConnection, Connection, Node

_LOGGER = logging.getLogger(__name__)


def _get_element_type(element: Element[str]) -> str:
    """Get the display type name for a model element."""
    if isinstance(element, Battery):
        return "battery"
    if isinstance(element, Node):
        return "node"
    if isinstance(element, BatteryBalanceConnection):
        return "balance"
    if isinstance(element, Connection):
        return "connection"
    return "unknown"


def _get_parent_device(name: str) -> str:
    """Extract parent device name from a model element name.

    Model elements follow naming patterns like:
    - "Battery:undercharge" -> "Battery"
    - "Battery:node" -> "Battery"
    - "Switchboard" -> "Switchboard" (no colon = top-level device)
    """
    return name.split(":")[0] if ":" in name else name


def create_graph_visualization(
    network: Network,
    output_path: str,
    title: str,
    *,
    generate_png: bool = True,
) -> None:
    """Create a graph visualization of the network topology.

    Uses the Network object to extract model elements and their connections,
    showing the actual structure created by the adapter layer with grouping
    by parent device element.
    """
    # Create directed graph
    graph: nx.DiGraph[str] = nx.DiGraph()

    # Color map for model element types
    node_color_map = {
        "battery": "#98df8a",  # Light green
        "node": "#c7c7c7",  # Light gray
        "balance": "#c5b0d5",  # Light purple
        "connection": "#aec7e8",  # Light blue
    }

    # Color map for device group backgrounds (lighter versions)
    group_color_map = {
        "battery": "#d4f0c8",  # Very light green
        "node": "#e8e8e8",  # Very light gray
        "solar": "#ffe4c4",  # Light orange/peach
        "grid": "#d4e5f7",  # Light blue
        "load": "#f5d5d5",  # Light red/pink
        "inverter": "#e6d8f0",  # Light purple
    }

    # Track parent devices for grouping
    device_groups: dict[str, list[str]] = defaultdict(list)

    # First pass: add all non-connection elements as nodes
    for name, element in network.elements.items():
        if isinstance(element, Connection):
            continue  # Handle connections as edges

        element_type = _get_element_type(element)
        parent_device = _get_parent_device(name)
        fillcolor = node_color_map.get(element_type, "lightgray")

        graph.add_node(
            name,
            color=fillcolor,
            element_type=element_type,
            parent_device=parent_device,
        )
        device_groups[parent_device].append(name)

    # Second pass: add connections as edges
    for name, element in network.elements.items():
        if not isinstance(element, Connection):
            continue

        source = element.source
        target = element.target

        # Ensure both endpoints exist as nodes
        if source not in graph.nodes():
            parent = _get_parent_device(source)
            graph.add_node(source, color="lightgray", element_type="unknown", parent_device=parent)
            device_groups[parent].append(source)
        if target not in graph.nodes():
            parent = _get_parent_device(target)
            graph.add_node(target, color="lightgray", element_type="unknown", parent_device=parent)
            device_groups[parent].append(target)

        # Determine edge style based on connection type
        edge_style = "balance" if isinstance(element, BatteryBalanceConnection) else "power"
        graph.add_edge(source, target, name=name, style=edge_style)

    if len(graph.nodes()) == 0:
        _LOGGER.warning("No nodes to visualize")
        return

    # Use spring layout for better visual organization
    pos = nx.spring_layout(graph, k=2.5, iterations=100, seed=42)  # type: ignore[no-untyped-call]

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_title(title, fontsize=14, pad=20)

    # Draw bounding boxes for device groups (groups with more than 1 node)
    for device_name, nodes in device_groups.items():
        if len(nodes) < 2:
            continue  # Skip groups with single node

        # Get positions of all nodes in this group
        node_positions = [pos[node] for node in nodes if node in pos]
        if not node_positions:
            continue

        xs = [p[0] for p in node_positions]
        ys = [p[1] for p in node_positions]

        # Calculate bounding box with padding
        padding = 0.3
        min_x, max_x = min(xs) - padding, max(xs) + padding
        min_y, max_y = min(ys) - padding, max(ys) + padding

        # Determine group color based on first node's element type or device name
        first_node = nodes[0]
        element_type = graph.nodes[first_node].get("element_type", "")
        group_color = group_color_map.get(element_type, group_color_map.get(device_name.lower(), "#f0f0f0"))

        # Draw rounded rectangle for the group
        rect = mpatches.FancyBboxPatch(
            (min_x, min_y),
            max_x - min_x,
            max_y - min_y,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=group_color,
            edgecolor="#999999",
            linewidth=1.5,
            alpha=0.6,
            zorder=0,
        )
        ax.add_patch(rect)

        # Add device label above the group
        label_y = max_y + 0.05
        ax.text(
            (min_x + max_x) / 2,
            label_y,
            device_name,
            fontsize=10,
            fontweight="bold",
            ha="center",
            va="bottom",
            color="#333333",
        )

    # Draw nodes with type-specific colors
    for node in graph.nodes():
        node_color = graph.nodes[node].get("color", "lightgray")
        element_type = graph.nodes[node].get("element_type", "")

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

        # Draw node label - abbreviate names with colons
        display_name = node.split(":")[-1] if ":" in node else node
        label_text = f"{display_name}\n({element_type})"
        nx.draw_networkx_labels(  # type: ignore[no-untyped-call]
            graph, pos, labels={node: label_text}, font_size=7, font_weight="bold", ax=ax
        )

    # Draw edges with arrows, different styles for balance vs power connections
    power_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("style") == "power"]
    balance_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("style") == "balance"]

    if power_edges:
        nx.draw_networkx_edges(  # type: ignore[no-untyped-call]
            graph,
            pos,
            edgelist=power_edges,
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

    if balance_edges:
        nx.draw_networkx_edges(  # type: ignore[no-untyped-call]
            graph,
            pos,
            edgelist=balance_edges,
            edge_color="#9467bd",  # Purple for balance connections
            arrows=True,
            arrowsize=20,
            arrowstyle="->",
            width=1.5,
            style="dashed",
            node_size=2000,
            min_source_margin=15,
            min_target_margin=15,
            ax=ax,
            connectionstyle="arc3,rad=0.15",
        )

    # Draw edge labels showing connection names (abbreviated)
    edge_labels = {(u, v): d.get("name", "").split(":")[-1] for u, v, d in graph.edges(data=True)}
    nx.draw_networkx_edge_labels(  # type: ignore[no-untyped-call]
        graph,
        pos,
        edge_labels=edge_labels,
        font_size=6,
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
