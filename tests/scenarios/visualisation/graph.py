"""Graph visualization for HAEO network topology.

This module creates network topology diagrams showing model elements and their
connections as created by the adapter layer. Uses the Network object to extract
the actual model elements after optimization, grouped by parent device.
"""

from collections import defaultdict
import logging
import math
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


def _compute_hierarchical_positions(
    device_groups: dict[str, list[str]],
    graph: "nx.DiGraph[str]",
) -> dict[str, tuple[float, float]]:
    """Compute positions using a two-level hierarchical layout.

    First computes group positions based on inter-group connectivity,
    then positions nodes within each group based on their internal connections.
    Uses spectral layout (with spring fallback) for both levels to produce
    topologically meaningful layouts.
    """
    pos: dict[str, tuple[float, float]] = {}

    sorted_groups = sorted(device_groups.items(), key=lambda x: -len(x[1]))
    n_groups = len(sorted_groups)
    if n_groups == 0:
        return pos

    # First, compute internal layouts for each group to determine group sizes
    group_internal_pos: dict[str, dict[str, tuple[float, float]]] = {}
    group_radii: dict[str, float] = {}

    for device_name, nodes in sorted_groups:
        if len(nodes) == 1:
            group_internal_pos[device_name] = {nodes[0]: (0.0, 0.0)}
            group_radii[device_name] = 0.3  # Minimum radius for single node
        else:
            # Compute internal layout - use circular if no internal edges
            subgraph = graph.subgraph(nodes).copy()
            internal_edges = subgraph.number_of_edges()

            if internal_edges > 0:
                # Has internal structure - use spectral/spring
                sub_pos = _compute_layout(subgraph, scale=1.0)
            else:
                # No internal edges - arrange in a circle
                sub_pos = {}
                n = len(nodes)
                radius = 0.3 + 0.15 * n  # Scale radius with node count
                for i, node in enumerate(nodes):
                    angle = 2 * math.pi * i / n
                    sub_pos[node] = (radius * math.cos(angle), radius * math.sin(angle))

            # Normalize to fit within a reasonable radius
            if sub_pos:
                max_dist = max(math.sqrt(x**2 + y**2) for x, y in sub_pos.values())
                group_radii[device_name] = max(0.3, max_dist + 0.2)
            else:
                group_radii[device_name] = 0.3

            group_internal_pos[device_name] = sub_pos

    # Build a metagraph of group connections for group-level layout
    group_graph: nx.Graph[str] = nx.Graph()
    node_to_group = {node: device for device, nodes in device_groups.items() for node in nodes}

    for device in device_groups:
        group_graph.add_node(device)

    # Add edges between groups based on connections between their nodes
    for edge in graph.edges():
        src_group = node_to_group.get(edge[0])
        dst_group = node_to_group.get(edge[1])
        if src_group and dst_group and src_group != dst_group:
            if group_graph.has_edge(src_group, dst_group):
                group_graph[src_group][dst_group]["weight"] += 1
            else:
                group_graph.add_edge(src_group, dst_group, weight=1)

    # Compute initial group positions
    raw_group_pos = _compute_layout(group_graph, scale=1.0)

    # Scale group positions to prevent overlap based on group radii
    max_radius = max(group_radii.values()) if group_radii else 0.5
    min_spacing = max_radius * 3.5  # Minimum spacing between group centers

    # Scale the group positions to ensure proper spacing
    group_pos: dict[str, tuple[float, float]] = {}
    for device, (x, y) in raw_group_pos.items():
        group_pos[device] = (x * min_spacing, y * min_spacing)

    # Combine group positions with internal positions
    for device_name, internal_pos in group_internal_pos.items():
        group_center = group_pos.get(device_name, (0.0, 0.0))
        for node, (x, y) in internal_pos.items():
            pos[node] = (group_center[0] + x, group_center[1] + y)

    return pos


def _compute_layout(
    graph: "nx.Graph[str] | nx.DiGraph[str]",
    scale: float = 1.0,
) -> dict[str, tuple[float, float]]:
    """Compute layout using spectral with spring fallback.

    Spectral layout produces topologically meaningful positions but requires
    a connected graph with at least 3 nodes. Falls back to spring layout for
    smaller or disconnected graphs.
    """
    if len(graph) == 0:
        return {}

    if len(graph) == 1:
        node = next(iter(graph.nodes()))
        return {node: (0.0, 0.0)}

    # Spectral layout needs at least 3 nodes to produce meaningful positions
    # (2-node graphs produce degenerate eigenvectors that collapse to origin)
    if len(graph) >= 3:
        try:
            undirected = graph.to_undirected() if graph.is_directed() else graph
            if nx.is_connected(undirected):
                raw_pos: dict[str, tuple[float, float]] = nx.spectral_layout(graph, scale=scale)  # type: ignore[no-untyped-call]
                # Refine with spring layout for better spacing
                return nx.spring_layout(graph, pos=raw_pos, k=scale * 0.5, iterations=50, seed=42)  # type: ignore[no-untyped-call]
        except Exception:
            pass

    # Fall back to spring layout for small graphs or disconnected graphs
    return nx.spring_layout(graph, k=scale * 0.5, iterations=100, seed=42)  # type: ignore[no-untyped-call]


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

    # Use hierarchical group-based layout
    pos = _compute_hierarchical_positions(device_groups, graph)

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_title(title, fontsize=14, pad=20)

    # Font settings for nodes
    node_font_size = 8

    # Pre-compute node labels and dimensions based on text length
    node_labels: dict[str, str] = {}
    node_sizes: dict[str, tuple[float, float]] = {}  # (width, height) in data units

    # Size nodes based on text content (character-based sizing)
    # These factors are tuned for the coordinate system used by the layout
    char_width = 0.08  # Approximate width per character
    line_height = 0.18  # Approximate height per line
    padding = 0.12  # Padding around text

    for node in graph.nodes():
        element_type = graph.nodes[node].get("element_type", "")
        display_name = node.split(":")[-1] if ":" in node else node
        label_text = f"{display_name}\n({element_type})"
        node_labels[node] = label_text

        # Calculate size based on text content
        lines = label_text.split("\n")
        max_line_len = max(len(line) for line in lines)
        n_lines = len(lines)

        width = max_line_len * char_width + 2 * padding
        height = n_lines * line_height + 2 * padding
        node_sizes[node] = (width, height)

    # Calculate approximate node radius for bounding box padding (use max dimension)
    max_node_dim = max(max(w, h) for w, h in node_sizes.values()) if node_sizes else 0.3
    node_radius = max_node_dim / 2

    # Draw bounding boxes for ALL device groups
    for device_name, nodes in device_groups.items():
        # Get positions of all nodes in this group
        node_positions = [pos[node] for node in nodes if node in pos]
        if not node_positions:
            continue

        xs = [p[0] for p in node_positions]
        ys = [p[1] for p in node_positions]

        # Calculate bounding box with tight padding
        padding = node_radius + 0.15
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
            boxstyle="round,pad=0.02,rounding_size=0.1",
            facecolor=group_color,
            edgecolor="#888888",
            linewidth=1.5,
            alpha=0.7,
            zorder=0,
        )
        ax.add_patch(rect)

        # Add device label above the group
        label_y = max_y + 0.08
        ax.text(
            (min_x + max_x) / 2,
            label_y,
            device_name,
            fontsize=9,
            fontweight="bold",
            ha="center",
            va="bottom",
            color="#333333",
        )

    # Draw nodes as rounded rectangles with text-based sizing
    for node in graph.nodes():
        node_color = graph.nodes[node].get("color", "lightgray")
        x, y = pos[node]
        width, height = node_sizes[node]
        label_text = node_labels[node]

        # Draw rounded rectangle for node
        node_rect = mpatches.FancyBboxPatch(
            (x - width / 2, y - height / 2),
            width,
            height,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor=node_color,
            edgecolor="black",
            linewidth=1.5,
            zorder=2,
        )
        ax.add_patch(node_rect)

        # Draw node label centered in rectangle
        ax.text(
            x,
            y,
            label_text,
            fontsize=node_font_size,
            fontweight="bold",
            ha="center",
            va="center",
            zorder=3,
        )

    # Draw edges with arrows, different styles for balance vs power connections
    power_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("style") == "power"]
    balance_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("style") == "balance"]
    # Calculate node_size for edge margin calculations (approximate based on max node dimension)
    # networkx node_size is in points^2, so we need to convert from data units
    avg_node_size = 1500  # Approximate size for edge margin calculations

    if power_edges:
        nx.draw_networkx_edges(  # type: ignore[no-untyped-call]
            graph,
            pos,
            edgelist=power_edges,
            edge_color="#555555",
            arrows=True,
            arrowsize=15,
            arrowstyle="->",
            width=1.5,
            node_size=avg_node_size,
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
            arrowsize=15,
            arrowstyle="->",
            width=1.2,
            style="dashed",
            node_size=avg_node_size,
            min_source_margin=15,
            min_target_margin=15,
            ax=ax,
            connectionstyle="arc3,rad=0.15",
        )

    # Draw edge labels showing connection name and type (matching node label style)
    # Use simple text annotations instead of draw_networkx_edge_labels
    # to avoid compatibility issues with curved edges
    for u, v, d in graph.edges(data=True):
        name = d.get("name", "")
        display_name = name.split(":")[-1] if ":" in name else name
        edge_type = d.get("style", "connection")
        label = f"{display_name}\n({edge_type})"
        if display_name and u in pos and v in pos:
            # Position label at midpoint of edge
            x = (pos[u][0] + pos[v][0]) / 2
            y = (pos[u][1] + pos[v][1]) / 2
            ax.annotate(
                label,
                (x, y),
                fontsize=6,
                fontweight="bold",
                ha="center",
                va="center",
                color="#333333",
                bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "edgecolor": "none", "alpha": 0.9},
            )

    # Remove axis and set equal aspect ratio
    ax.axis("off")
    ax.set_aspect("equal")
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
