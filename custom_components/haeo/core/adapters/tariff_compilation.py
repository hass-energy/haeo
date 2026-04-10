"""Policy compilation: converts policy configs into tagged power flow constraints.

This module implements the compilation pipeline that transforms user-configured
policy rules into model-layer constructs: tag IDs on connections, source_tag
on nodes, and scoped pricing segments.

The pipeline runs as a post-processing step in collect_model_elements(),
after all adapters have produced their model element configs but before
the configs are passed to Network.add().
"""

from typing import Any

from custom_components.haeo.core.model.elements.segments.segment import DEFAULT_TAG


def compile_policies(
    elements: list[dict[str, Any]],
    policy_configs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compile policy rules into tagged power flow constraints.

    Args:
        elements: All model element configs (nodes and connections).
        policy_configs: List of policy rule configs, each with:
            - sources: list of node names, or ["*"] for any
            - destinations: list of node names, or ["*"] for any
            - price_source_target: $/kWh or None
            - price_target_source: $/kWh or None

    Returns:
        Modified elements list with tags and scoped segments injected.

    """
    if not policy_configs:
        return elements

    # Separate connections and nodes (work with mutable copies)
    connections: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []
    for elem in elements:
        if elem.get("element_type") == "connection":
            connections.append(dict(elem))
        elif elem.get("element_type") == "node":
            nodes.append(dict(elem))
        else:
            other.append(elem)

    if not connections:
        return elements

    # Build node name set
    node_names: set[str] = {n["name"] for n in nodes}

    # Build connection index: node_name -> list of connections touching that node
    conn_by_node: dict[str, list[dict[str, Any]]] = {}
    for conn in connections:
        source = conn.get("source", "")
        target = conn.get("target", "")
        conn_by_node.setdefault(source, []).append(conn)
        conn_by_node.setdefault(target, []).append(conn)

    # Step 1: Tag assignment — each source node in any policy gets a unique tag
    tag_counter = 1
    tag_map: dict[str, int] = {}  # node_name -> tag_id

    for policy in policy_configs:
        sources = policy.get("sources", [])
        if sources == ["*"]:
            for name in node_names:
                if name not in tag_map:
                    tag_map[name] = tag_counter
                    tag_counter += 1
        else:
            for name in sources:
                if name not in tag_map:
                    tag_map[name] = tag_counter
                    tag_counter += 1

    if not tag_map:
        return elements

    # Collect all active tags
    all_tags = sorted({DEFAULT_TAG, *tag_map.values()})

    # Step 2: Connection tagging — every connection gets all active tags
    for conn in connections:
        conn["tags"] = list(all_tags)

    # Step 3: Source enforcement — set source_tag on source nodes
    # This tells the Node to enforce that only its tag can carry outbound power
    node_by_name: dict[str, dict[str, Any]] = {n["name"]: n for n in nodes}
    for source_name, tag_id in tag_map.items():
        if source_name in node_by_name:
            node_by_name[source_name]["source_tag"] = tag_id

    # Step 4: Scoped pricing injection at destination connections
    for idx, policy in enumerate(policy_configs):
        sources = policy.get("sources", [])
        destinations = policy.get("destinations", [])
        price_st = policy.get("price_source_target")
        price_ts = policy.get("price_target_source")

        if price_st is None and price_ts is None:
            continue

        # Resolve source tags
        if sources == ["*"]:
            source_tags = list(tag_map.values())
        else:
            source_tags = [tag_map[s] for s in sources if s in tag_map]

        # Resolve destination nodes
        if destinations == ["*"]:
            dest_nodes = list(node_names)
        else:
            dest_nodes = [d for d in destinations if d in node_names]

        # For each source tag × destination node, inject pricing
        for source_tag in source_tags:
            for dest_node in dest_nodes:
                dest_connections = conn_by_node.get(dest_node, [])
                for conn in dest_connections:
                    segments = dict(conn.get("segments", {}))
                    seg_name = f"_policy_{idx}_t{source_tag}_to_{dest_node}"

                    # Ensure unique segment name
                    final_name = seg_name
                    counter = 0
                    while final_name in segments:
                        counter += 1
                        final_name = f"{seg_name}_{counter}"

                    # Build scoped pricing segment
                    pricing_spec: dict[str, Any] = {
                        "segment_type": "pricing",
                        "tag": source_tag,
                    }

                    # Determine pricing direction based on connection orientation
                    if conn.get("target") == dest_node:
                        if price_st is not None:
                            pricing_spec["price_source_target"] = price_st
                    elif conn.get("source") == dest_node:
                        if price_st is not None:
                            pricing_spec["price_target_source"] = price_st

                    if "price_source_target" in pricing_spec or "price_target_source" in pricing_spec:
                        segments[final_name] = pricing_spec
                        conn["segments"] = segments

    return [*other, *nodes, *connections]
