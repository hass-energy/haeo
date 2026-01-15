"""Graph visualization for HAEO network topology.

Creates network topology diagrams showing model elements and their connections,
grouped by parent device. Uses the Network object after optimization.
"""

from collections import defaultdict
from dataclasses import dataclass
import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx

from custom_components.haeo.model import Network
from custom_components.haeo.model.element import Element
from custom_components.haeo.model.elements import Battery, BatteryBalanceConnection, Connection, Node

# Use non-GUI backend
mpl.use("Agg")

# Fix SVG hash salt for consistent output
mpl.rcParams["svg.hashsalt"] = "42"

if TYPE_CHECKING:
    from matplotlib.axes import Axes

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================


@dataclass(frozen=True)
class StyleConfig:
    """Visual styling configuration for the graph."""

    # Node colors by element type
    node_colors: dict[str, str]
    # Group background colors
    group_colors: dict[str, str]
    # Edge colors
    power_edge_color: str = "#555555"
    balance_edge_color: str = "#9467bd"
    # Text sizing (character-based)
    char_width: float = 0.08
    line_height: float = 0.18
    text_padding: float = 0.12
    node_font_size: int = 8
    edge_font_size: int = 6
    group_font_size: int = 9


DEFAULT_STYLE = StyleConfig(
    node_colors={
        "battery": "#98df8a",
        "node": "#c7c7c7",
        "balance": "#c5b0d5",
        "connection": "#aec7e8",
    },
    group_colors={
        "battery": "#d4f0c8",
        "node": "#e8e8e8",
        "solar": "#ffe4c4",
        "grid": "#d4e5f7",
        "load": "#f5d5d5",
        "inverter": "#e6d8f0",
    },
)


# =============================================================================
# Graph Building
# =============================================================================


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
    """Extract parent device name from element name (before the colon)."""
    return name.split(":")[0] if ":" in name else name


def _get_display_name(name: str) -> str:
    """Get display name for element (after the colon, or full name)."""
    return name.split(":")[-1] if ":" in name else name


def build_graph(
    network: Network,
    style: StyleConfig,
) -> tuple["nx.DiGraph[str]", dict[str, list[str]]]:
    """Build a networkx graph from the Network model.

    Returns:
        Tuple of (graph, device_groups) where device_groups maps
        parent device names to their contained node names.

    """
    graph: nx.DiGraph[str] = nx.DiGraph()
    device_groups: dict[str, list[str]] = defaultdict(list)

    # Add non-connection elements as nodes (sorted for deterministic order)
    for name, element in sorted(network.elements.items()):
        if isinstance(element, Connection):
            continue

        element_type = _get_element_type(element)
        parent_device = _get_parent_device(name)
        color = style.node_colors.get(element_type, "lightgray")

        graph.add_node(name, color=color, element_type=element_type)
        device_groups[parent_device].append(name)

    # Add connections as edges (sorted for deterministic order)
    for name, element in sorted(network.elements.items()):
        if not isinstance(element, Connection):
            continue

        source, target = element.source, element.target

        # Ensure endpoints exist
        for endpoint in (source, target):
            if endpoint not in graph.nodes():
                parent = _get_parent_device(endpoint)
                graph.add_node(endpoint, color="lightgray", element_type="unknown")
                device_groups[parent].append(endpoint)

        edge_style = "balance" if isinstance(element, BatteryBalanceConnection) else "power"
        graph.add_edge(source, target, name=name, style=edge_style)

    # Sort device_groups and their node lists for deterministic order
    sorted_groups = {k: sorted(v) for k, v in sorted(device_groups.items())}
    return graph, sorted_groups


# =============================================================================
# Layout Computation
# =============================================================================


def _compute_spring_layout(
    graph: "nx.Graph[str] | nx.DiGraph[str]",
    scale: float = 1.0,
) -> dict[str, tuple[float, float]]:
    """Compute layout using spring layout with fixed seed for determinism."""
    if len(graph) == 0:
        return {}
    if len(graph) == 1:
        return {next(iter(graph.nodes())): (0.0, 0.0)}

    return nx.spring_layout(graph, k=scale * 0.5, iterations=100, seed=42)  # type: ignore[no-untyped-call]


def _compute_group_internal_layout(
    nodes: list[str],
    graph: "nx.DiGraph[str]",
) -> tuple[dict[str, tuple[float, float]], float]:
    """Compute layout for nodes within a single group.

    Returns:
        Tuple of (positions, radius) where positions are relative to group center.

    """
    # Sort nodes for deterministic layout
    sorted_nodes = sorted(nodes)

    if len(sorted_nodes) == 1:
        return {sorted_nodes[0]: (0.0, 0.0)}, 0.3

    # Create subgraph with nodes in sorted order for deterministic layout
    subgraph: nx.DiGraph[str] = nx.DiGraph()
    for node in sorted_nodes:
        subgraph.add_node(node, **graph.nodes[node])
    for u, v in sorted(graph.edges()):
        if u in sorted_nodes and v in sorted_nodes:
            subgraph.add_edge(u, v, **graph.edges[u, v])

    if subgraph.number_of_edges() > 0:
        # Has internal structure - use spring layout
        pos = _compute_spring_layout(subgraph, scale=1.0)
    else:
        # No internal edges - arrange in a circle
        pos = {}
        n = len(sorted_nodes)
        radius = 0.3 + 0.15 * n
        for i, node in enumerate(sorted_nodes):
            angle = 2 * math.pi * i / n
            pos[node] = (radius * math.cos(angle), radius * math.sin(angle))

    max_dist = max(math.sqrt(x**2 + y**2) for x, y in pos.values()) if pos else 0.0
    return pos, max(0.3, max_dist + 0.2)


def compute_positions(
    graph: "nx.DiGraph[str]",
    device_groups: dict[str, list[str]],
) -> dict[str, tuple[float, float]]:
    """Compute hierarchical positions with groups and internal layouts."""
    if not device_groups:
        return {}

    # Compute internal layouts for each group (sorted for determinism)
    group_layouts: dict[str, dict[str, tuple[float, float]]] = {}
    group_radii: dict[str, float] = {}

    for device_name in sorted(device_groups.keys()):
        nodes = device_groups[device_name]
        internal_pos, radius = _compute_group_internal_layout(nodes, graph)
        group_layouts[device_name] = internal_pos
        group_radii[device_name] = radius

    # Build metagraph of inter-group connections (sorted for determinism)
    group_graph: nx.Graph[str] = nx.Graph()
    node_to_group = {n: d for d, nodes in device_groups.items() for n in nodes}

    for device in sorted(device_groups.keys()):
        group_graph.add_node(device)

    for u, v in sorted(graph.edges()):
        src_group, dst_group = node_to_group.get(u), node_to_group.get(v)
        if src_group and dst_group and src_group != dst_group:
            if group_graph.has_edge(src_group, dst_group):
                group_graph[src_group][dst_group]["weight"] += 1
            else:
                group_graph.add_edge(src_group, dst_group, weight=1)

    # Compute group positions and scale to prevent overlap
    raw_group_pos = _compute_spring_layout(group_graph, scale=1.0)
    max_radius = max(group_radii.values()) if group_radii else 0.5
    spacing = max_radius * 3.5

    # Combine group positions with internal positions (sorted for determinism)
    pos: dict[str, tuple[float, float]] = {}
    for device_name in sorted(group_layouts.keys()):
        internal_pos = group_layouts[device_name]
        gx, gy = raw_group_pos.get(device_name, (0.0, 0.0))
        gx, gy = gx * spacing, gy * spacing
        for node in sorted(internal_pos.keys()):
            x, y = internal_pos[node]
            pos[node] = (gx + x, gy + y)

    return pos


# =============================================================================
# Label and Size Computation
# =============================================================================


def compute_node_labels_and_sizes(
    graph: "nx.DiGraph[str]",
    style: StyleConfig,
) -> tuple[dict[str, str], dict[str, tuple[float, float]]]:
    """Compute display labels and sizes for all nodes.

    Returns:
        Tuple of (labels, sizes) where sizes are (width, height) in data units.

    """
    labels: dict[str, str] = {}
    sizes: dict[str, tuple[float, float]] = {}

    for node in graph.nodes():
        element_type = graph.nodes[node].get("element_type", "")
        display_name = _get_display_name(node)
        label = f"{display_name}\n({element_type})"
        labels[node] = label

        lines = label.split("\n")
        max_len = max(len(line) for line in lines)
        width = max_len * style.char_width + 2 * style.text_padding
        height = len(lines) * style.line_height + 2 * style.text_padding
        sizes[node] = (width, height)

    return labels, sizes


def compute_edge_labels(graph: "nx.DiGraph[str]") -> dict[tuple[str, str], str]:
    """Compute display labels for all edges."""
    labels: dict[tuple[str, str], str] = {}
    for u, v, d in graph.edges(data=True):
        name = d.get("name", "")
        display_name = _get_display_name(name)
        edge_type = d.get("style", "connection")
        labels[(u, v)] = f"{display_name}\n({edge_type})"
    return labels


# =============================================================================
# Rendering
# =============================================================================


def _draw_device_groups(
    ax: "Axes",
    graph: "nx.DiGraph[str]",
    device_groups: dict[str, list[str]],
    pos: dict[str, tuple[float, float]],
    node_radius: float,
    style: StyleConfig,
) -> None:
    """Draw bounding boxes for device groups."""
    # Sort for deterministic drawing order
    for device_name in sorted(device_groups.keys()):
        nodes = device_groups[device_name]
        node_positions = [pos[n] for n in nodes if n in pos]
        if not node_positions:
            continue

        xs = [p[0] for p in node_positions]
        ys = [p[1] for p in node_positions]
        pad = node_radius + 0.15
        min_x, max_x = min(xs) - pad, max(xs) + pad
        min_y, max_y = min(ys) - pad, max(ys) + pad

        # Determine color from first node's type or device name
        first_type = graph.nodes[nodes[0]].get("element_type", "")
        color = style.group_colors.get(first_type, style.group_colors.get(device_name.lower(), "#f0f0f0"))

        rect = mpatches.FancyBboxPatch(
            (min_x, min_y),
            max_x - min_x,
            max_y - min_y,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            facecolor=color,
            edgecolor="#888888",
            linewidth=1.5,
            alpha=0.7,
            zorder=0,
        )
        ax.add_patch(rect)

        ax.text(
            (min_x + max_x) / 2,
            max_y + 0.08,
            device_name,
            fontsize=style.group_font_size,
            fontweight="bold",
            ha="center",
            va="bottom",
            color="#333333",
        )


def _draw_nodes(
    ax: "Axes",
    graph: "nx.DiGraph[str]",
    pos: dict[str, tuple[float, float]],
    labels: dict[str, str],
    sizes: dict[str, tuple[float, float]],
    style: StyleConfig,
) -> None:
    """Draw nodes as rounded rectangles with labels."""
    # Sort nodes for deterministic drawing order
    for node in sorted(graph.nodes()):
        color = graph.nodes[node].get("color", "lightgray")
        x, y = pos[node]
        width, height = sizes[node]

        rect = mpatches.FancyBboxPatch(
            (x - width / 2, y - height / 2),
            width,
            height,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor=color,
            edgecolor="black",
            linewidth=1.5,
            zorder=2,
        )
        ax.add_patch(rect)

        ax.text(
            x,
            y,
            labels[node],
            fontsize=style.node_font_size,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=3,
        )


def _draw_edges(
    ax: "Axes",
    graph: "nx.DiGraph[str]",
    pos: dict[str, tuple[float, float]],
    style: StyleConfig,
) -> None:
    """Draw edges with arrows."""
    # Sort edges for deterministic drawing order
    power_edges = sorted((u, v) for u, v, d in graph.edges(data=True) if d.get("style") == "power")
    balance_edges = sorted((u, v) for u, v, d in graph.edges(data=True) if d.get("style") == "balance")

    if power_edges:
        nx.draw_networkx_edges(  # type: ignore[no-untyped-call]
            graph,
            pos,
            edgelist=power_edges,
            edge_color=style.power_edge_color,
            width=1.5,
            connectionstyle="arc3,rad=0.1",
            arrows=True,
            arrowsize=15,
            arrowstyle="->",
            node_size=1500,
            min_source_margin=15,
            min_target_margin=15,
            ax=ax,
        )

    if balance_edges:
        nx.draw_networkx_edges(  # type: ignore[no-untyped-call]
            graph,
            pos,
            edgelist=balance_edges,
            edge_color=style.balance_edge_color,
            width=1.2,
            style="dashed",
            connectionstyle="arc3,rad=0.15",
            arrows=True,
            arrowsize=15,
            arrowstyle="->",
            node_size=1500,
            min_source_margin=15,
            min_target_margin=15,
            ax=ax,
        )


def _draw_edge_labels(
    ax: "Axes",
    pos: dict[str, tuple[float, float]],
    edge_labels: dict[tuple[str, str], str],
    style: StyleConfig,
) -> None:
    """Draw labels on edges."""
    # Sort for deterministic drawing order
    for (u, v), label in sorted(edge_labels.items()):
        if not label.split("\n")[0] or u not in pos or v not in pos:
            continue
        x = (pos[u][0] + pos[v][0]) / 2
        y = (pos[u][1] + pos[v][1]) / 2
        ax.annotate(
            label,
            (x, y),
            fontsize=style.edge_font_size,
            fontweight="bold",
            ha="center",
            va="center",
            color="#333333",
            bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "edgecolor": "none", "alpha": 0.9},
        )


# =============================================================================
# Main Entry Point
# =============================================================================


def create_graph_visualization(
    network: Network,
    output_path: str,
    title: str,
    *,
    generate_png: bool = True,
    style: StyleConfig | None = None,
) -> None:
    """Create a graph visualization of the network topology.

    Args:
        network: The Network object containing model elements.
        output_path: Path for the output SVG file.
        title: Title displayed on the graph.
        generate_png: Whether to also generate a PNG file.
        style: Optional custom styling configuration.

    """
    style = style or DEFAULT_STYLE

    # Build graph
    graph, device_groups = build_graph(network, style)
    if len(graph.nodes()) == 0:
        _LOGGER.warning("No nodes to visualize")
        return

    # Compute layout
    pos = compute_positions(graph, device_groups)

    # Compute labels and sizes
    node_labels, node_sizes = compute_node_labels_and_sizes(graph, style)
    edge_labels = compute_edge_labels(graph)
    max_node_dim = max(max(w, h) for w, h in node_sizes.values()) if node_sizes else 0.3
    node_radius = max_node_dim / 2

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_title(title, fontsize=14, pad=20)

    # Render layers (back to front)
    _draw_device_groups(ax, graph, device_groups, pos, node_radius, style)
    _draw_edges(ax, graph, pos, style)
    _draw_nodes(ax, graph, pos, node_labels, node_sizes, style)
    _draw_edge_labels(ax, pos, edge_labels, style)

    # Finalize
    ax.axis("off")
    ax.set_aspect("equal")
    plt.tight_layout()

    # Save outputs
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_path, format="svg", bbox_inches="tight", dpi=300, metadata={"Date": None})
    _LOGGER.info("Graph visualization saved to %s", output_path)

    if generate_png:
        png_path = str(output_path).replace(".svg", ".png")
        plt.savefig(png_path, format="png", bbox_inches="tight", dpi=300)
        _LOGGER.info("Graph visualization saved to %s", png_path)

    plt.close(fig)
