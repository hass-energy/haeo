/** ELK-based layout for HAEO network topology. */

import ELK, { type ElkExtendedEdge, type ElkNode, type ElkPort } from "elkjs/lib/elk.bundled.js";
import type { TopologyData, TopologySegment } from "./types";

export interface LayoutNode {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  type: string;
  isGroup: boolean;
  children: LayoutNode[];
  ports: LayoutPort[];
}

export interface LayoutPort {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  side: "EAST" | "WEST";
}

export interface LayoutSegmentNodule {
  id: string;
  type: string;
  x: number;
  y: number;
}

export interface LayoutEdge {
  name: string;
  source: string;
  target: string;
  points: Array<{ x: number; y: number }>;
  segments: LayoutSegmentNodule[];
}

export interface LayoutResult {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
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

const NODE_WIDTH = 130;
const NODE_HEIGHT = 45;
const GROUP_HEADER = 24;
const GROUP_PAD = 12;
const PORT_SIZE = 8;

export async function computeLayout(topology: TopologyData): Promise<LayoutResult> {
  const elk = new ELK();

  // Each group is a compound node containing its model-layer sub-elements.
  // Connections (edges) stay OUTSIDE groups, with segments as nodules along edges.
  const elkChildren: ElkNode[] = [];

  for (const [groupName, members] of Object.entries(topology.groups)) {
    const groupType = topology.nodes.find((n) => members.includes(n.name) === true)?.type ?? "unknown";

    // Sub-elements within this group
    const children: ElkNode[] = members.map((name) => ({
      id: name,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      labels: [{ text: name }],
    }));

    // Add segment pill nodes for connections belonging to this group
    const internalEdges: ElkExtendedEdge[] = [];
    for (const edge of topology.edges) {
      const visibleSegs = edge.segments.filter((s) => s.type !== "PassthroughSegment");
      if (visibleSegs.length > 0 && members.includes(edge.target)) {
        // Segment pill belongs to the TARGET group (adapter defines segments)
        const pillId = `pill:${edge.name}`;
        const pillWidth = visibleSegs.length * 28 + 8;
        children.push({
          id: pillId,
          width: pillWidth,
          height: 24,
          labels: [{ text: edge.name }],
        });
        // Internal edge from pill to the target element
        internalEdges.push({
          id: `internal:${edge.name}`,
          sources: [pillId],
          targets: [edge.target],
        });
      }
    }

    // Ports for connections entering/leaving this group
    const ports: ElkPort[] = [];
    for (const edge of topology.edges) {
      if (members.includes(edge.source)) {
        ports.push({
          id: `port:${edge.name}:out`,
          width: PORT_SIZE,
          height: PORT_SIZE,
          layoutOptions: { "org.eclipse.elk.port.side": "EAST" },
        });
      }
      if (members.includes(edge.target)) {
        ports.push({
          id: `port:${edge.name}:in`,
          width: PORT_SIZE,
          height: PORT_SIZE,
          layoutOptions: { "org.eclipse.elk.port.side": "WEST" },
        });
      }
    }

    elkChildren.push({
      id: `group:${groupName}`,
      labels: [{ text: `${groupName} (${groupType})` }],
      children,
      ports,
      edges: internalEdges,
      layoutOptions: {
        "org.eclipse.elk.padding": `[top=${GROUP_HEADER + GROUP_PAD},left=${GROUP_PAD},bottom=${GROUP_PAD},right=${GROUP_PAD}]`,
        "org.eclipse.elk.nodeLabels.placement": "H_LEFT V_TOP INSIDE",
      },
    });
  }

  // Edges between groups (connections) — segments become labels, not nodes
  const elkEdges: ElkExtendedEdge[] = topology.edges.map((edge) => ({
    id: `edge:${edge.name}`,
    sources: [`port:${edge.name}:out`],
    targets: [`port:${edge.name}:in`],
    labels: [{ text: edge.name, width: edge.name.length * 6, height: 12 }],
  }));

  const layoutGraph = await elk.layout({
    id: "root",
    children: elkChildren,
    edges: elkEdges,
    layoutOptions: {
      "org.eclipse.elk.algorithm": "layered",
      "org.eclipse.elk.direction": "RIGHT",
      "org.eclipse.elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "org.eclipse.elk.spacing.nodeNode": "30",
      "org.eclipse.elk.spacing.edgeNode": "15",
      "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "60",
      "org.eclipse.elk.portConstraints": "FIXED_SIDE",
      "org.eclipse.elk.randomSeed": "42",
      "org.eclipse.elk.layered.spacing.edgeEdgeBetweenLayers": "15",
    },
  });

  return extractLayout(layoutGraph, topology);
}

function extractLayout(graph: ElkNode, topology: TopologyData): LayoutResult {
  const nodes: LayoutNode[] = [];

  for (const child of graph.children ?? []) {
    if (!child.id.startsWith("group:")) continue;
    const groupName = child.id.slice(6);
    const groupType =
      topology.nodes.find((n) => topology.groups[groupName]?.includes(n.name) === true)?.type ?? "unknown";

    const children: LayoutNode[] = (child.children ?? []).map((inner) => ({
      id: inner.id,
      x: inner.x ?? 0,
      y: inner.y ?? 0,
      width: inner.width ?? NODE_WIDTH,
      height: inner.height ?? NODE_HEIGHT,
      type: groupType,
      isGroup: false,
      children: [],
      ports: [],
    }));

    const ports: LayoutPort[] = (child.ports ?? []).map((port) => ({
      id: port.id,
      x: port.x ?? 0,
      y: port.y ?? 0,
      width: port.width ?? PORT_SIZE,
      height: port.height ?? PORT_SIZE,
      side: port.layoutOptions?.["org.eclipse.elk.port.side"] === "WEST" ? ("WEST" as const) : ("EAST" as const),
    }));

    nodes.push({
      id: child.id,
      x: child.x ?? 0,
      y: child.y ?? 0,
      width: child.width ?? 200,
      height: child.height ?? 100,
      type: groupType,
      isGroup: true,
      children,
      ports,
    });
  }

  // Extract edges with segment nodules positioned along the path
  const edges: LayoutEdge[] = [];
  for (const elkEdge of graph.edges ?? []) {
    const topoEdge = topology.edges.find((e) => `edge:${e.name}` === elkEdge.id);
    if (topoEdge === undefined) continue;

    const sections = elkEdge.sections ?? [];
    const points: Array<{ x: number; y: number }> = [];
    for (const section of sections) {
      points.push(section.startPoint);
      for (const bp of section.bendPoints ?? []) {
        points.push(bp);
      }
      points.push(section.endPoint);
    }

    // Distribute segment nodules along the edge path
    const visibleSegments = topoEdge.segments.filter((s) => s.type !== "PassthroughSegment");
    const segmentNodules = distributeAlongPath(points, visibleSegments);

    edges.push({
      name: topoEdge.name,
      source: topoEdge.source,
      target: topoEdge.target,
      points,
      segments: segmentNodules,
    });
  }

  return {
    nodes,
    edges,
    width: (graph.width ?? 800) + 20,
    height: (graph.height ?? 400) + 20,
  };
}

function distributeAlongPath(
  points: Array<{ x: number; y: number }>,
  segments: TopologySegment[]
): LayoutSegmentNodule[] {
  if (segments.length === 0 || points.length < 2) return [];

  let totalLength = 0;
  const cumLengths = [0];
  for (let i = 1; i < points.length; i++) {
    const dx = points[i]!.x - points[i - 1]!.x;
    const dy = points[i]!.y - points[i - 1]!.y;
    totalLength += Math.sqrt(dx * dx + dy * dy);
    cumLengths.push(totalLength);
  }
  if (totalLength === 0) return [];

  return segments.map((seg, i) => {
    const t = (i + 1) / (segments.length + 1);
    const dist = t * totalLength;

    let idx = 0;
    while (idx < cumLengths.length - 1 && cumLengths[idx + 1]! < dist) idx++;

    const segStart = cumLengths[idx]!;
    const segEnd = cumLengths[idx + 1] ?? segStart;
    const localT = segEnd > segStart ? (dist - segStart) / (segEnd - segStart) : 0;

    const p0 = points[idx]!;
    const p1 = points[idx + 1] ?? p0;

    return {
      id: seg.id,
      type: seg.type,
      x: p0.x + (p1.x - p0.x) * localT,
      y: p0.y + (p1.y - p0.y) * localT,
    };
  });
}
