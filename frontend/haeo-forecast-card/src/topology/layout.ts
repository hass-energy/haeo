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

export interface PolicyPillLayout {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  connectionName: string;
  terms: Array<{ policyName: string; tag: number }>;
}

export interface LayoutResult {
  groups: LayoutGroup[];
  externalEdges: LayoutEdge[];
  policyPills: PolicyPillLayout[];
  legend: { x: number; y: number; width: number; height: number } | null;
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
 * Get the owner group of a connection from its name prefix (e.g. "Grid:import" → "Grid").
 */
function connectionOwner(edgeName: string): string {
  const colon = edgeName.indexOf(":");
  return colon >= 0 ? edgeName.slice(0, colon) : "";
}

/**
 * Find the hub node — the one with the most unique peer group connections.
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

  for (const [groupName, members] of Object.entries(topology.groups)) {
    const children: ElkNode[] = [];
    const internalEdges: ElkExtendedEdge[] = [];
    const ports: ElkPort[] = [];

    for (const name of members) {
      children.push({ id: name, width: NODE_W, height: NODE_H });
    }

    for (const edge of topology.edges) {
      const sg = findGroup(topology, edge.source);
      const tg = findGroup(topology, edge.target);
      if (sg === tg) continue;

      const isReversed = reversed.has(edge.name);
      const layoutSource = isReversed ? tg : sg;
      const layoutTarget = isReversed ? sg : tg;
      const owner = connectionOwner(edge.name);
      const visible = edge.segments.filter((s) => s.type !== "PassthroughSegment");

      // Layout source group gets outgoing port (+ pill if owner)
      if (groupName === layoutSource) {
        const outPortId = `port:${edge.name}:layout-out`;
        ports.push({
          id: outPortId,
          width: PORT_SZ,
          height: PORT_SZ,
          layoutOptions: { "org.eclipse.elk.port.side": "EAST" },
        });

        if (owner === groupName && visible.length > 0) {
          const pillId = `pill:${edge.name}`;
          children.push({
            id: pillId,
            width: visible.length * PILL_CELL_W + 8,
            height: PILL_H,
          });
          internalEdges.push({
            id: `int:${edge.name}:a`,
            sources: [members[0] ?? ""],
            targets: [pillId],
          });
          internalEdges.push({
            id: `int:${edge.name}:b`,
            sources: [pillId],
            targets: [outPortId],
          });
        } else {
          internalEdges.push({
            id: `int:${edge.name}:out`,
            sources: [members[0] ?? ""],
            targets: [outPortId],
          });
        }
      }

      // Layout target group gets incoming port (+ pill if owner)
      if (groupName === layoutTarget) {
        const inPortId = `port:${edge.name}:layout-in`;
        ports.push({
          id: inPortId,
          width: PORT_SZ,
          height: PORT_SZ,
          layoutOptions: { "org.eclipse.elk.port.side": "WEST" },
        });

        if (owner === groupName && visible.length > 0) {
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
            targets: [members[0] ?? ""],
          });
        } else {
          internalEdges.push({
            id: `int:${edge.name}:in`,
            sources: [inPortId],
            targets: [members[0] ?? ""],
          });
        }
      }
    }

    // Sort ports by edge name within each side so bidirectional pairs
    // have consistent y-ordering across groups (prevents crossings).
    ports.sort((a, b) => {
      // First by side (WEST before EAST)
      const sideA = a.layoutOptions?.["org.eclipse.elk.port.side"] ?? "";
      const sideB = b.layoutOptions?.["org.eclipse.elk.port.side"] ?? "";
      if (sideA !== sideB) return sideA < sideB ? -1 : 1;
      // Then by edge name
      const nameA = a.id.replace(/^port:|:layout-(in|out)$/g, "");
      const nameB = b.id.replace(/^port:|:layout-(in|out)$/g, "");
      return nameA.localeCompare(nameB);
    });

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
        "org.eclipse.elk.portConstraints": "FIXED_ORDER",
        "org.eclipse.elk.spacing.nodeNode": "10",
        "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "15",
      },
    });
  }

  // Build lookup: connection name → policy terms placed on it
  const policyTermsByConnection = new Map<string, Array<{ policyName: string; tag: number }>>();
  for (const policy of topology.policies ?? []) {
    for (const term of policy.terms) {
      if (!policyTermsByConnection.has(term.connection)) {
        policyTermsByConnection.set(term.connection, []);
      }
      policyTermsByConnection.get(term.connection)!.push({
        policyName: policy.name,
        tag: term.tag,
      });
    }
  }

  // Route edges through ELK, inserting policy pill nodes where needed
  for (const edge of topology.edges) {
    const sg = findGroup(topology, edge.source);
    const tg = findGroup(topology, edge.target);
    if (sg === tg) continue;

    const policyTerms = policyTermsByConnection.get(edge.name);
    if (policyTerms != null && policyTerms.length > 0) {
      // Create a pill node for this connection's policies
      const pillId = `policy-pill:${edge.name}`;
      const pillW = policyTerms.length * 32 + 8;
      elkChildren.push({
        id: pillId,
        width: pillW,
        height: PILL_H,
      });
      // Edge: source port → pill → target port
      elkEdges.push({
        id: `ext:${edge.name}:a`,
        sources: [`port:${edge.name}:layout-out`],
        targets: [pillId],
      });
      elkEdges.push({
        id: `ext:${edge.name}:b`,
        sources: [pillId],
        targets: [`port:${edge.name}:layout-in`],
      });
    } else {
      elkEdges.push({
        id: `ext:${edge.name}`,
        sources: [`port:${edge.name}:layout-out`],
        targets: [`port:${edge.name}:layout-in`],
      });
    }
  }

  // Add VLAN legend as a layout node if there are active VLANs
  const activeVlans = new Set<number>();
  for (const edge of topology.edges) {
    if (edge.tags != null) {
      for (const t of edge.tags) activeVlans.add(t);
    }
  }
  if (activeVlans.size > 0) {
    const legendH = 24 + activeVlans.size * 16;
    elkChildren.push({
      id: "legend:vlans",
      width: 90,
      height: legendH,
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
      "org.eclipse.elk.spacing.edgeEdge": "12",
      "org.eclipse.elk.spacing.edgeNode": "12",
      "org.eclipse.elk.randomSeed": "42",
    },
  });

  return extractResult(graph, topology, reversed, policyTermsByConnection);
}

function extractResult(
  graph: ElkNode,
  topology: TopologyData,
  reversed: Set<string>,
  policyTermsByConnection: Map<string, Array<{ policyName: string; tag: number }>>
): LayoutResult {
  const groups: LayoutGroup[] = [];

  for (const child of graph.children ?? []) {
    // Skip policy pill nodes (handled separately)
    if (child.id.startsWith("policy-pill:")) continue;
    if (child.id.startsWith("legend:")) continue;
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
      return { name: e.id, source: "", target: "", points, internal: true, reversed: false };
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

  // Extract external edges — combine half-edges for policy-split connections
  const halfEdgePoints = new Map<string, Array<{ x: number; y: number }>>();
  const directEdges: Array<{ id: string; points: Array<{ x: number; y: number }> }> = [];

  for (const e of graph.edges ?? []) {
    const sections = e.sections ?? [];
    const points: Array<{ x: number; y: number }> = [];
    for (const s of sections) {
      points.push(s.startPoint);
      for (const bp of s.bendPoints ?? []) points.push(bp);
      points.push(s.endPoint);
    }

    // Check if this is a half-edge (ext:Name:a or ext:Name:b)
    const halfMatch = /^ext:(.+):(a|b)$/.exec(e.id);
    if (halfMatch != null) {
      halfEdgePoints.set(e.id, points);
    } else {
      directEdges.push({ id: e.id, points });
    }
  }

  const externalEdges: LayoutEdge[] = [];

  // Direct edges (no policy pill)
  for (const { id, points } of directEdges) {
    const edgeName = id.replace("ext:", "");
    const topoEdge = topology.edges.find((te) => te.name === edgeName);
    const isReversed = reversed.has(edgeName);
    externalEdges.push({
      name: id,
      source: topoEdge?.source ?? "",
      target: topoEdge?.target ?? "",
      points,
      internal: false,
      reversed: isReversed,
    });
  }

  // Combined half-edges
  for (const edge of topology.edges) {
    const aKey = `ext:${edge.name}:a`;
    const bKey = `ext:${edge.name}:b`;
    const ptsA = halfEdgePoints.get(aKey);
    const ptsB = halfEdgePoints.get(bKey);
    if (ptsA == null || ptsB == null) continue;
    // Join: drop last point of A (pill center) since B starts there
    const combined = [...ptsA.slice(0, -1), ...ptsB];
    const isReversed = reversed.has(edge.name);
    externalEdges.push({
      name: `ext:${edge.name}`,
      source: edge.source,
      target: edge.target,
      points: combined,
      internal: false,
      reversed: isReversed,
    });
  }

  // Extract policy pill positions
  const policyPills: PolicyPillLayout[] = [];
  for (const child of graph.children ?? []) {
    if (!child.id.startsWith("policy-pill:")) continue;
    const connectionName = child.id.replace("policy-pill:", "");
    const terms = policyTermsByConnection.get(connectionName) ?? [];
    policyPills.push({
      id: child.id,
      x: child.x ?? 0,
      y: child.y ?? 0,
      width: child.width ?? 40,
      height: child.height ?? PILL_H,
      connectionName,
      terms,
    });
  }

  // Extract legend position
  const legendNode = (graph.children ?? []).find((c) => c.id === "legend:vlans");
  const legend =
    legendNode != null
      ? { x: legendNode.x ?? 0, y: legendNode.y ?? 0, width: legendNode.width ?? 90, height: legendNode.height ?? 40 }
      : null;

  return {
    groups,
    externalEdges,
    policyPills,
    legend,
    width: (graph.width ?? 800) + 20,
    height: (graph.height ?? 400) + 20,
  };
}
