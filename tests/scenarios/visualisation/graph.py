"""Graph visualization for HAEO network topology.

This module creates network topology diagrams showing model elements and their
connections as created by the adapter layer. Uses the Network object to extract
the actual model elements after optimization.
"""

import logging
from pathlib import Path

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


def create_graph_visualization(
    network: Network,
    output_path: str,
    title: str,
    *,
    generate_png: bool = True,
) -> None:
    """Create a graph visualization of the network topology.

    Uses the Network object to extract model elements and their connections,
    showing the actual structure created by the adapter layer.
    """
    # Create directed graph
    graph: nx.DiGraph[str] = nx.DiGraph()

    # Color map for model element types
    color_map = {
        "battery": "#98df8a",  # Light green
        "node": "#c7c7c7",  # Light gray
        "balance": "#c5b0d5",  # Light purple
        "connection": "#aec7e8",  # Light blue
    }

    # First pass: add all non-connection elements as nodes
    for name, element in network.elements.items():
        if isinstance(element, Connection):
            continue  # Handle connections as edges

        element_type = _get_element_type(element)
        fillcolor = color_map.get(element_type, "lightgray")
        graph.add_node(
            name,
            color=fillcolor,
            element_type=element_type,
        )

    # Second pass: add connections as edges
    for name, element in network.elements.items():
        if not isinstance(element, Connection):
            continue

        source = element.source
        target = element.target

        # Ensure both endpoints exist as nodes
        if source not in graph.nodes():
            graph.add_node(source, color="lightgray", element_type="unknown")
        if target not in graph.nodes():
            graph.add_node(target, color="lightgray", element_type="unknown")

        # Determine edge style based on connection type
        edge_style = "balance" if isinstance(element, BatteryBalanceConnection) else "power"
        graph.add_edge(source, target, name=name, style=edge_style)

    if len(graph.nodes()) == 0:
        _LOGGER.warning("No nodes to visualize")
        return

    # Use spring layout for better visual organization
    pos = nx.spring_layout(graph, k=2.0, iterations=50, seed=42)  # type: ignore[no-untyped-call]

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_title(title, fontsize=14, pad=20)

    # Draw nodes with type-specific colors
    for node in graph.nodes():
        node_color = graph.nodes[node].get("color", "lightgray")
        element_type = graph.nodes[node].get("element_type", "")

        nx.draw_networkx_nodes(  # type: ignore[no-untyped-call]
            graph,
            pos,
            nodelist=[node],
            node_color=node_color,
            node_size=2500,
            node_shape="o",
            edgecolors="black",
            linewidths=2,
            ax=ax,
        )

        # Draw node label - abbreviate names with colons
        display_name = node.split(":")[-1] if ":" in node else node
        label_text = f"{display_name}\n({element_type})"
        nx.draw_networkx_labels(  # type: ignore[no-untyped-call]
            graph, pos, labels={node: label_text}, font_size=8, font_weight="bold", ax=ax
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
            node_size=2500,
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
            node_size=2500,
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
