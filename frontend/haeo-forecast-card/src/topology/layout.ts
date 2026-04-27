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

function findGroup(topology: TopologyData, nodeName: string): string {
  return Object.entries(topology.groups).find(([, m]) => m.includes(nodeName))?.[0] ?? "";
}

/**
 * Find the hub node — the one with the most connections.
 */
function findHub(topology: TopologyData): string {
  const counts = new Map<string, number>();
  for (const edge of topology.edges) {
    const sg = findGroup(topology, edge.source);
    const tg = findGroup(topology, edge.target);
    counts.set(sg, (counts.get(sg) ?? 0) + 1);
    counts.set(tg, (counts.get(tg) ?? 0) + 1);
  }
  let hub = "";
  let max = 0;
  for (const [name, count] of counts) {
    if (count > max) {
      max = count;
      hub = name;
    }
  }
  return hub;
}

/**
 * BFS from hub to orient all edges outward (hub → leaf direction).
 * Returns a set of edge names that should be reversed for layout.
 */
function orientEdgesFromHub(topology: TopologyData, hub: string): Set<string> {
  // Build adjacency: group → [{edge, peerGroup, isSourceSide}]
  const adj = new Map<string, Array<{ edge: string; peer: string; isSource: boolean }>>();
  for (const edge of topology.edges) {
    const sg = findGroup(topology, edge.source);
    const tg = findGroup(topology, edge.target);
    if (sg === tg) continue;
    if (!adj.has(sg)) adj.set(sg, []);
    if (!adj.has(tg)) adj.set(tg, []);
    adj.get(sg)!.push({ edge: edge.name, peer: tg, isSource: true });
    adj.get(tg)!.push({ edge: edge.name, peer: sg, isSource: false });
  }

  // BFS from hub — edges should point away from hub
  const visited = new Set<string>();
  const reversed = new Set<string>();
  const queue = [hub];
  visited.add(hub);

  while (queue.length > 0) {
    const current = queue.shift()!;
    for (const { edge, peer, isSource } of adj.get(current) ?? []) {
      if (visited.has(peer)) continue;
      visited.add(peer);
      queue.push(peer);
      // Edge should go current→peer (outward from hub)
      // If current is actually the target (not source), we need to reverse
      if (!isSource) {
        reversed.add(edge);
      }
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

    // For each connection, add pills and ports inside the appropriate group.
    // Port ownership follows the LAYOUT direction (outward from hub),
    // not the actual edge direction.
    for (const edge of topology.edges) {
      const sg = findGroup(topology, edge.source);
      const tg = findGroup(topology, edge.target);
      if (sg === tg) continue;

      const isReversed = reversed.has(edge.name);
      // Layout source (outward from hub) = actual source if not reversed
      const layoutSource = isReversed ? tg : sg;
      const layoutTarget = isReversed ? sg : tg;

      const visible = edge.segments.filter((s) => s.type !== "PassthroughSegment");

      // Source group gets outgoing port + pill
      if (groupName === layoutSource) {
        const outPortId = `port:${edge.name}:layout-out`;
        ports.push({ id: outPortId, width: PORT_SZ, height: PORT_SZ });

        if (visible.length > 0) {
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
          const sourceNode = members[0] ?? "";
          internalEdges.push({
            id: `int:${edge.name}`,
            sources: [sourceNode],
            targets: [outPortId],
          });
        }
      }

      // Target group gets incoming port
      if (groupName === layoutTarget) {
        const inPortId = `port:${edge.name}:layout-in`;
        ports.push({ id: inPortId, width: PORT_SZ, height: PORT_SZ });
        const targetNode = members[0] ?? "";
        internalEdges.push({
          id: `int:${edge.name}:in`,
          sources: [inPortId],
          targets: [targetNode],
        });
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
        "org.eclipse.elk.spacing.nodeNode": "10",
        "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "15",
      },
    });
  }

  // External edges — all oriented outward from hub
  for (const edge of topology.edges) {
    const sg = findGroup(topology, edge.source);
    const tg = findGroup(topology, edge.target);
    if (sg === tg) continue;

    elkEdges.push({
      id: `ext:${edge.name}`,
      sources: [`port:${edge.name}:layout-out`],
      targets: [`port:${edge.name}:layout-in`],
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
      "org.eclipse.elk.randomSeed": "42",
    },
  });

  return extractResult(graph, topology, reversed);
}

function extractResult(graph: ElkNode, topology: TopologyData, reversed: Set<string>): LayoutResult {
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

  const externalEdges: LayoutEdge[] = (graph.edges ?? []).map((e) => {
    const edgeName = e.id.replace("ext:", "");
    const topoEdge = topology.edges.find((te) => te.name === edgeName);
    const sections = e.sections ?? [];
    const points: Array<{ x: number; y: number }> = [];
    for (const s of sections) {
      points.push(s.startPoint);
      for (const bp of s.bendPoints ?? []) points.push(bp);
      points.push(s.endPoint);
    }
    const isReversed = reversed.has(edgeName);
    return {
      name: e.id,
      source: topoEdge?.source ?? "",
      target: topoEdge?.target ?? "",
      points: isReversed ? [...points].reverse() : points,
      internal: false,
      reversed: isReversed,
    };
  });

  return {
    groups,
    externalEdges,
    width: (graph.width ?? 800) + 20,
    height: (graph.height ?? 400) + 20,
  };
}
