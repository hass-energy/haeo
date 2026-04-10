"""Tariff compilation: converts tariff configs into tagged power flow constraints.

This module implements the compilation pipeline that transforms user-configured
tariff rules into model-layer constructs: tag IDs on connections and scoped
pricing/filtering segments.

The pipeline runs as a post-processing step in collect_model_elements(),
after all adapters have produced their model element configs but before
the configs are passed to Network.add().
"""

from typing import Any

from custom_components.haeo.core.model.elements.segments.segment import DEFAULT_TAG


def compile_tariffs(
    elements: list[dict[str, Any]],
    tariff_configs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compile tariff rules into tagged power flow constraints on connections.

    Args:
        elements: All model element configs (nodes and connections).
        tariff_configs: List of tariff rule configs, each with:
            - sources: list of node names, or ["*"] for any
            - destinations: list of node names, or ["*"] for any
            - price_source_target: $/kWh or None
            - price_target_source: $/kWh or None

    Returns:
        Modified elements list with tags and scoped segments injected.

    """
    if not tariff_configs:
        return elements

    # Separate connections from other elements (work with mutable copies)
    connections: list[dict[str, Any]] = []
    non_connections: list[dict[str, Any]] = []
    for elem in elements:
        if elem.get("element_type") == "connection":
            connections.append(dict(elem))  # mutable copy
        else:
            non_connections.append(elem)

    if not connections:
        return elements

    # Build node set and connection adjacency
    node_names: set[str] = set()
    for elem in non_connections:
        if elem.get("element_type") == "node":
            node_names.add(elem["name"])

    # Build connection index: node_name -> list of connections touching that node
    conn_by_node: dict[str, list[dict[str, Any]]] = {}
    for conn in connections:
        source = conn.get("source", "")
        target = conn.get("target", "")
        conn_by_node.setdefault(source, []).append(conn)
        conn_by_node.setdefault(target, []).append(conn)

    # Step 1: Tag assignment — each source node in any tariff gets a unique tag
    tag_counter = 1
    tag_map: dict[str, int] = {}  # node_name -> tag_id

    for tariff in tariff_configs:
        sources = tariff.get("sources", [])
        if sources == ["*"]:
            # "any" source: assign tags to all nodes
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

    # Step 3: Source enforcement — at each source node's connections,
    # only that source's tag can flow outbound. Block other tags.
    for source_name, tag_id in tag_map.items():
        source_connections = conn_by_node.get(source_name, [])
        for conn in source_connections:
            segments = dict(conn.get("segments", {}))

            # For each tag that is NOT this source's tag, block outbound flow
            other_tags = [t for t in all_tags if t != tag_id and t != DEFAULT_TAG]
            for other_tag in other_tags:
                seg_name = f"_enforce_{source_name}_block_t{other_tag}"
                # Determine direction: if this source is the connection's source,
                # block source→target for other tags. If target, block target→source.
                if conn.get("source") == source_name:
                    segments[seg_name] = {
                        "segment_type": "power_limit",
                        "tag": other_tag,
                        "max_power_source_target": 0.0,
                    }
                elif conn.get("target") == source_name:
                    segments[seg_name] = {
                        "segment_type": "power_limit",
                        "tag": other_tag,
                        "max_power_target_source": 0.0,
                    }

            # Also block tag 0 (default) from carrying source power outbound
            # — all power from this source must be on its own tag
            seg_name_default = f"_enforce_{source_name}_block_t0"
            if conn.get("source") == source_name:
                segments[seg_name_default] = {
                    "segment_type": "power_limit",
                    "tag": DEFAULT_TAG,
                    "max_power_source_target": 0.0,
                }
            elif conn.get("target") == source_name:
                segments[seg_name_default] = {
                    "segment_type": "power_limit",
                    "tag": DEFAULT_TAG,
                    "max_power_target_source": 0.0,
                }

            conn["segments"] = segments

    # Step 4: Segment injection — for each tariff, add scoped pricing
    # at the destination connection (the discriminating point)
    for idx, tariff in enumerate(tariff_configs):
        sources = tariff.get("sources", [])
        destinations = tariff.get("destinations", [])
        price_st = tariff.get("price_source_target")
        price_ts = tariff.get("price_target_source")

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
                    seg_name = f"_tariff_{idx}_t{source_tag}_to_{dest_node}"

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
                        # Power flowing source→target reaches the dest node
                        if price_st is not None:
                            pricing_spec["price_source_target"] = price_st
                    elif conn.get("source") == dest_node:
                        # Power flowing target→source reaches the dest node
                        if price_st is not None:
                            pricing_spec["price_target_source"] = price_st

                    # Only add if there's actually a price to apply
                    if "price_source_target" in pricing_spec or "price_target_source" in pricing_spec:
                        segments[final_name] = pricing_spec
                        conn["segments"] = segments

    return [*non_connections, *connections]
