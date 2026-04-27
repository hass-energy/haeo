/**
 * Topology layout using ELK's layered algorithm.
 *
 * Strategy: orient all edges outward from the hub node (most connections)
 * to create a tree-like DAG. ELK's layered algorithm handles DAGs well,
 * producing clean left-to-right layouts. Actual edge directions are
 * preserved for rendering arrows.
 */

import ELK, { type ElkExtendedEdge, type ElkNode, type ElkPort } from "elkjs/lib/elk.bundled.js";
import type { TopologyData, TopologySegment } from "./types";

export interface LayoutNode {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  type: string;
  isPill: boolean;
  segments: TopologySegment[];
  children: LayoutNode[];
  ports: LayoutPort[];
}

export interface LayoutPort {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  side: "EAST" | "WEST" | "NORTH" | "SOUTH";
}

export interface LayoutEdge {
  name: string;
  source: string;
  target: string;
  points: Array<{ x: number; y: number }>;
  internal: boolean;
  /** True if the edge was flipped for layout — arrow should point backward. */
  reversed: boolean;
}

export interface LayoutGroup {
  id: string;
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  children: LayoutNode[];
  ports: LayoutPort[];
  internalEdges: LayoutEdge[];
}

export interface LayoutResult {
  groups: LayoutGroup[];
  externalEdges: LayoutEdge[];
  width: number;
  height: number;
}

export const NODE_STYLES: Record<string, { color: string; icon: string }> = {
  battery: { color: "#4CAF50", icon: "🔋" },
  node: { color: "#90CAF9", icon: "⚡" },
  grid: { color: "#FF9800", icon: "🏭" },
  solar: { color: "#FFD600", icon: "☀️" },
  load: { color: "#E91E63", icon: "🏠" },
  inverter: { color: "#9C27B0", icon: "🔄" },
  network: { color: "#607D8B", icon: "📡" },
  unknown: { color: "#BDBDBD", icon: "?" },
};

const NODE_W = 120;
const NODE_H = 36;
const PILL_CELL_W = 26;
const PILL_H = 20;
const PORT_SZ = 8;
const PAD = 14;
const HDR = 18;

type Side = "EAST" | "WEST" | "NORTH" | "SOUTH";

/**
 * Offset a polyline path perpendicular to each segment.
 * Positive offset = right side of travel direction.
 */
function offsetPath(points: Array<{ x: number; y: number }>, offset: number): Array<{ x: number; y: number }> {
  return points.map((p, i) => {
    // Use the direction from this point to the next (or previous for last point)
    const next = points[Math.min(i + 1, points.length - 1)]!;
    const prev = points[Math.max(i - 1, 0)]!;
    const dx = next.x - prev.x;
    const dy = next.y - prev.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len === 0) return { ...p };
    // Perpendicular: rotate 90° clockwise
    return { x: p.x + (dy / len) * offset, y: p.y - (dx / len) * offset };
  });
}

function findGroup(topology: TopologyData, nodeName: string): string {
  return Object.entries(topology.groups).find(([, m]) => m.includes(nodeName))?.[0] ?? "";
}

/**
 * Find the hub node — the one with the most unique peer group connections.
 * Ties broken by name to be deterministic.
 */
function findHub(topology: TopologyData): string {
  const peerCounts = new Map<string, Set<string>>();
  for (const edge of topology.edges) {
    const sg = findGroup(topology, edge.source);
    const tg = findGroup(topology, edge.target);
    if (sg === tg) continue;
    if (!peerCounts.has(sg)) peerCounts.set(sg, new Set());
    if (!peerCounts.has(tg)) peerCounts.set(tg, new Set());
    peerCounts.get(sg)!.add(tg);
    peerCounts.get(tg)!.add(sg);
  }
  let hub = "";
  let max = 0;
  for (const [name, peers] of peerCounts) {
    if (
      peers.size > max ||
      (peers.size === max && name.length > hub.length) ||
      (peers.size === max && name.length === hub.length && name > hub)
    ) {
      max = peers.size;
      hub = name;
    }
  }
  return hub;
}

/**
 * BFS from hub to orient ALL edges outward (hub → leaf direction).
 * All edges between the same pair of groups get the same layout direction,
 * determined by the BFS tree. This gives ELK a clean DAG.
 */
function orientEdgesFromHub(topology: TopologyData, hub: string): Set<string> {
  const adj = new Map<string, Array<{ peer: string }>>();
  for (const edge of topology.edges) {
    const sg = findGroup(topology, edge.source);
    const tg = findGroup(topology, edge.target);
    if (sg === tg) continue;
    if (!adj.has(sg)) adj.set(sg, []);
    if (!adj.has(tg)) adj.set(tg, []);
    adj.get(sg)!.push({ peer: tg });
    adj.get(tg)!.push({ peer: sg });
  }

  // BFS to determine parent→child for each group pair
  const visited = new Set<string>();
  const pairDirection = new Map<string, string>();
  const queue = [hub];
  visited.add(hub);

  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const { peer } of adj.get(current) ?? []) {
      if (visited.has(peer)) continue;
      visited.add(peer);
      queue.push(peer);
      const pairKey = [current, peer].sort().join("--");
      pairDirection.set(pairKey, current);
    }
  }

  // Reverse any edge whose actual source doesn't match the BFS layout source
  const reversed = new Set<string>();
  for (const edge of topology.edges) {
    const sg = findGroup(topology, edge.source);
    const tg = findGroup(topology, edge.target);
    if (sg === tg) continue;
    const pairKey = [sg, tg].sort().join("--");
    const layoutSource = pairDirection.get(pairKey);
    if (layoutSource !== undefined && layoutSource !== sg) {
      reversed.add(edge.name);
    }
  }

  return reversed;
}

export async function computeLayout(topology: TopologyData): Promise<LayoutResult> {
  const elk = new ELK();
  const hub = findHub(topology);
  const reversed = orientEdgesFromHub(topology, hub);

  const elkChildren: ElkNode[] = [];
  const elkEdges: ElkExtendedEdge[] = [];

  // Build group subgraphs
  for (const [groupName, members] of Object.entries(topology.groups)) {
    const children: ElkNode[] = [];
    const internalEdges: ElkExtendedEdge[] = [];
    const ports: ElkPort[] = [];

    // Model element nodes
    for (const name of members) {
      children.push({ id: name, width: NODE_W, height: NODE_H });
    }

    // For each connection, add pills and ports.
    // Ports follow LAYOUT direction (outward from hub) for ELK.
    // Pills go in the ACTUAL source group (connection owner).
    for (const edge of topology.edges) {
      const sg = findGroup(topology, edge.source);
      const tg = findGroup(topology, edge.target);
      if (sg === tg) continue;

      const isReversed = reversed.has(edge.name);
      const layoutSource = isReversed ? tg : sg;
      const layoutTarget = isReversed ? sg : tg;

      const visible = edge.segments.filter((s) => s.type !== "PassthroughSegment");

      // Layout source group gets outgoing port
      if (groupName === layoutSource) {
        const outPortId = `port:${edge.name}:layout-out`;
        ports.push({ id: outPortId, width: PORT_SZ, height: PORT_SZ });

        if (!isReversed && visible.length > 0) {
          // Not reversed: pill in layout source (= actual source)
          const pillId = `pill:${edge.name}`;
          const sourceNode = members[0] ?? "";
          children.push({
            id: pillId,
            width: visible.length * PILL_CELL_W + 8,
            height: PILL_H,
          });
          internalEdges.push({
            id: `int:${edge.name}:a`,
            sources: [sourceNode],
            targets: [pillId],
          });
          internalEdges.push({
            id: `int:${edge.name}:b`,
            sources: [pillId],
            targets: [outPortId],
          });
        } else {
          // Reversed or no segments: direct element → port
          const sourceNode = members[0] ?? "";
          internalEdges.push({
            id: `int:${edge.name}`,
            sources: [sourceNode],
            targets: [outPortId],
          });
        }
      }

      // Layout target group gets incoming port
      if (groupName === layoutTarget) {
        const inPortId = `port:${edge.name}:layout-in`;
        ports.push({ id: inPortId, width: PORT_SZ, height: PORT_SZ });
        const targetNode = members[0] ?? "";

        if (isReversed && visible.length > 0) {
          // Reversed: pill in layout target (= actual source)
          const pillId = `pill:${edge.name}`;
          children.push({
            id: pillId,
            width: visible.length * PILL_CELL_W + 8,
            height: PILL_H,
          });
          internalEdges.push({
            id: `int:${edge.name}:in`,
            sources: [inPortId],
            targets: [pillId],
          });
          internalEdges.push({
            id: `int:${edge.name}:pill`,
            sources: [pillId],
            targets: [targetNode],
          });
        } else {
          internalEdges.push({
            id: `int:${edge.name}:in`,
            sources: [inPortId],
            targets: [targetNode],
          });
        }
      }
    }

    elkChildren.push({
      id: `group:${groupName}`,
      labels: [{ text: groupName }],
      children,
      ports,
      edges: internalEdges,
      layoutOptions: {
        "org.eclipse.elk.algorithm": "layered",
        "org.eclipse.elk.direction": "RIGHT",
        "org.eclipse.elk.padding": `[top=${HDR + PAD},left=${PAD},bottom=${PAD},right=${PAD}]`,
        "org.eclipse.elk.nodeLabels.placement": "H_LEFT V_TOP INSIDE",
        "org.eclipse.elk.portConstraints": "FREE",
        "org.eclipse.elk.spacing.nodeNode": "10",
        "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "15",
      },
    });
  }

  // External edges — deduplicate per group pair to prevent parallel crossings.
  // Multiple connections between the same pair share a single layout edge.
  const pairEdgeMap = new Map<string, string[]>();
  for (const edge of topology.edges) {
    const sg = findGroup(topology, edge.source);
    const tg = findGroup(topology, edge.target);
    if (sg === tg) continue;
    const isReversed = reversed.has(edge.name);
    const layoutSource = isReversed ? tg : sg;
    const layoutTarget = isReversed ? sg : tg;
    const pairKey = `${layoutSource}--${layoutTarget}`;
    if (!pairEdgeMap.has(pairKey)) pairEdgeMap.set(pairKey, []);
    pairEdgeMap.get(pairKey)!.push(edge.name);
  }

  // Create one ELK edge per pair, using the first connection's ports
  for (const [, edgeNames] of pairEdgeMap) {
    const firstName = edgeNames[0]!;
    elkEdges.push({
      id: `ext:${firstName}`,
      sources: [`port:${firstName}:layout-out`],
      targets: [`port:${firstName}:layout-in`],
    });
  }

  const graph: ElkNode = await elk.layout({
    id: "root",
    children: elkChildren,
    edges: elkEdges,
    layoutOptions: {
      "org.eclipse.elk.algorithm": "layered",
      "org.eclipse.elk.direction": "RIGHT",
      "org.eclipse.elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "org.eclipse.elk.spacing.nodeNode": "25",
      "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "40",
      "org.eclipse.elk.layered.mergeEdges": "true",
      "org.eclipse.elk.spacing.edgeEdge": "15",
      "org.eclipse.elk.spacing.edgeNode": "15",
      "org.eclipse.elk.randomSeed": "42",
    },
  });

  return extractResult(graph, topology, reversed, pairEdgeMap);
}

function extractResult(
  graph: ElkNode,
  topology: TopologyData,
  reversed: Set<string>,
  pairEdgeMap: Map<string, string[]>
): LayoutResult {
  const groups: LayoutGroup[] = [];

  for (const child of graph.children ?? []) {
    const groupName = child.id.replace("group:", "");
    const gType = topology.nodes.find((n) => topology.groups[groupName]?.includes(n.name) === true)?.type ?? "unknown";

    const children: LayoutNode[] = (child.children ?? []).map((inner) => {
      const isPill = inner.id.startsWith("pill:");
      const edgeName = isPill ? inner.id.slice(5) : "";
      const topoEdge = isPill ? topology.edges.find((e) => e.name === edgeName) : undefined;
      const segs = topoEdge?.segments.filter((s) => s.type !== "PassthroughSegment") ?? [];

      return {
        id: inner.id,
        x: inner.x ?? 0,
        y: inner.y ?? 0,
        width: inner.width ?? NODE_W,
        height: inner.height ?? NODE_H,
        type: isPill ? "pill" : gType,
        isPill,
        segments: segs,
        children: [],
        ports: [],
      };
    });

    const ports: LayoutPort[] = (child.ports ?? []).map((p) => ({
      id: p.id,
      x: p.x ?? 0,
      y: p.y ?? 0,
      width: p.width ?? PORT_SZ,
      height: p.height ?? PORT_SZ,
      side: (p.layoutOptions?.["org.eclipse.elk.port.side"] ?? "EAST") as Side,
    }));

    const internalEdges: LayoutEdge[] = (child.edges ?? []).map((e) => {
      const sections = e.sections ?? [];
      const points: Array<{ x: number; y: number }> = [];
      for (const s of sections) {
        points.push(s.startPoint);
        for (const bp of s.bendPoints ?? []) points.push(bp);
        points.push(s.endPoint);
      }
      return {
        name: e.id,
        source: "",
        target: "",
        points,
        internal: true,
        reversed: false,
      };
    });

    groups.push({
      id: child.id,
      type: gType,
      x: child.x ?? 0,
      y: child.y ?? 0,
      width: child.width ?? 200,
      height: child.height ?? 100,
      children,
      ports,
      internalEdges,
    });
  }

  // Expand deduped edges back to one LayoutEdge per connection
  const externalEdges: LayoutEdge[] = [];
  for (const e of graph.edges ?? []) {
    const primaryName = e.id.replace("ext:", "");
    const sections = e.sections ?? [];
    const points: Array<{ x: number; y: number }> = [];
    for (const s of sections) {
      points.push(s.startPoint);
      for (const bp of s.bendPoints ?? []) points.push(bp);
      points.push(s.endPoint);
    }

    // Find which pair this belongs to and get all edges in that pair
    for (const [, edgeNames] of pairEdgeMap) {
      if (edgeNames[0] !== primaryName) continue;
      const count = edgeNames.length;
      edgeNames.forEach((edgeName, idx) => {
        const topoEdge = topology.edges.find((te) => te.name === edgeName);
        const isReversed = reversed.has(edgeName);
        // Offset parallel edges perpendicular to the path
        const offset = count > 1 ? (idx - (count - 1) / 2) * 6 : 0;
        const offsetPoints = offset === 0 ? [...points] : offsetPath(points, offset);
        externalEdges.push({
          name: `ext:${edgeName}`,
          source: topoEdge?.source ?? "",
          target: topoEdge?.target ?? "",
          points: isReversed ? [...offsetPoints].reverse() : offsetPoints,
          internal: false,
          reversed: isReversed,
        });
      });
    }
  }

  return {
    groups,
    externalEdges,
    width: (graph.width ?? 800) + 20,
    height: (graph.height ?? 400) + 20,
  };
}
