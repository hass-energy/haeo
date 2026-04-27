/** Dagre-based layout for HAEO network topology. */

import dagre from "dagre";
import type { TopologyData, TopologySegment } from "./types";

export interface LayoutNode {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  type: string;
  group: string;
  isGroup: boolean;
}

export interface LayoutSegmentNodule {
  x: number;
  y: number;
  id: string;
  type: string;
  edgeName: string;
}

export interface LayoutEdge {
  name: string;
  source: string;
  target: string;
  points: Array<{ x: number; y: number }>;
  segments: LayoutSegmentNodule[];
}

export interface LayoutGroup {
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  members: string[];
}

export interface LayoutResult {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  groups: LayoutGroup[];
  width: number;
  height: number;
}

const NODE_WIDTH = 120;
const NODE_HEIGHT = 50;
const GROUP_PADDING = 20;

/** Element type to icon/color mapping. */
export const NODE_STYLES: Record<string, { color: string; icon: string }> = {
  battery: { color: "#4CAF50", icon: "🔋" },
  node: { color: "#90CAF9", icon: "⚡" },
  grid: { color: "#FF9800", icon: "🏭" },
  solar: { color: "#FFD600", icon: "☀️" },
  load: { color: "#E91E63", icon: "🏠" },
  inverter: { color: "#9C27B0", icon: "🔄" },
  unknown: { color: "#BDBDBD", icon: "?" },
};

export function computeLayout(topology: TopologyData): LayoutResult {
  const g = new dagre.graphlib.Graph({ compound: true });
  g.setGraph({
    rankdir: "LR",
    ranksep: 100,
    nodesep: 60,
    edgesep: 30,
    marginx: 40,
    marginy: 40,
  });
  g.setDefaultEdgeLabel(() => ({}));

  // Identify which groups have multiple members (worth grouping visually)
  const multiGroups = new Set(
    Object.entries(topology.groups)
      .filter(([, members]) => members.length > 1)
      .map(([name]) => name)
  );

  // Add group compound nodes
  for (const groupName of multiGroups) {
    g.setNode(`group:${groupName}`, {
      label: groupName,
      clusterLabelPos: "top",
      width: 0,
      height: 0,
    });
  }

  // Add nodes
  for (const node of topology.nodes) {
    g.setNode(node.name, {
      label: node.name,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    });
    if (multiGroups.has(node.group)) {
      g.setParent(node.name, `group:${node.group}`);
    }
  }

  // Add edges — account for segment nodules needing space
  for (const edge of topology.edges) {
    const visibleSegments = edge.segments.filter((s) => s.type !== "PassthroughSegment");
    g.setEdge(edge.source, edge.target, {
      label: edge.name,
      minlen: visibleSegments.length > 0 ? 2 : 1,
      width: visibleSegments.length * 24,
    });
  }

  dagre.layout(g);

  // Extract layout results
  const nodes: LayoutNode[] = [];
  const groups: LayoutGroup[] = [];

  for (const nodeId of g.nodes()) {
    const n = g.node(nodeId) as { x: number; y: number; width: number; height: number; label?: string } | undefined;
    if (n == null) continue;

    if (nodeId.startsWith("group:")) {
      const groupName = nodeId.slice(6);
      groups.push({
        name: groupName,
        x: n.x - n.width / 2,
        y: n.y - n.height / 2,
        width: n.width + GROUP_PADDING * 2,
        height: n.height + GROUP_PADDING * 2,
        members: topology.groups[groupName] ?? [],
      });
    } else {
      const topoNode = topology.nodes.find((tn) => tn.name === nodeId);
      nodes.push({
        id: nodeId,
        x: n.x,
        y: n.y,
        width: n.width,
        height: n.height,
        type: topoNode?.type ?? "unknown",
        group: topoNode?.group ?? nodeId,
        isGroup: false,
      });
    }
  }

  // Extract edges with segment nodule positions
  const edges: LayoutEdge[] = [];
  for (const edge of topology.edges) {
    const edgeData = g.edge(edge.source, edge.target) as { points?: Array<{ x: number; y: number }> } | undefined;
    if (edgeData?.points == null) continue;

    const points = edgeData.points.map((p: { x: number; y: number }) => ({
      x: p.x,
      y: p.y,
    }));

    // Place segment nodules evenly along the edge path
    const visibleSegments = edge.segments.filter((s) => s.type !== "PassthroughSegment");
    const segmentNodules = distributeSegments(points, visibleSegments, edge.name);

    edges.push({
      name: edge.name,
      source: edge.source,
      target: edge.target,
      points,
      segments: segmentNodules,
    });
  }

  // Compute overall dimensions
  const graph = g.graph() as { width?: number; height?: number };
  const width = (graph.width ?? 800) + 80;
  const height = (graph.height ?? 400) + 80;

  return { nodes, edges, groups, width, height };
}

/** Distribute segment nodules evenly along an edge path. */
function distributeSegments(
  points: Array<{ x: number; y: number }>,
  segments: TopologySegment[],
  edgeName: string
): LayoutSegmentNodule[] {
  if (segments.length === 0 || points.length < 2) return [];

  // Compute total path length
  let totalLength = 0;
  const lengths: number[] = [0];
  for (let i = 1; i < points.length; i++) {
    const dx = points[i]!.x - points[i - 1]!.x;
    const dy = points[i]!.y - points[i - 1]!.y;
    totalLength += Math.sqrt(dx * dx + dy * dy);
    lengths.push(totalLength);
  }

  if (totalLength === 0) return [];

  // Place segments evenly along the path
  const result: LayoutSegmentNodule[] = [];
  for (let i = 0; i < segments.length; i++) {
    const t = (i + 1) / (segments.length + 1);
    const targetDist = t * totalLength;

    // Find the segment of the path this falls on
    let segIdx = 0;
    while (segIdx < lengths.length - 1 && lengths[segIdx + 1]! < targetDist) {
      segIdx++;
    }

    const segStart = lengths[segIdx] ?? 0;
    const segEnd = lengths[segIdx + 1] ?? segStart;
    const segLen = segEnd - segStart;
    const localT = segLen > 0 ? (targetDist - segStart) / segLen : 0;

    const p0 = points[segIdx]!;
    const p1 = points[segIdx + 1] ?? p0;

    result.push({
      x: p0.x + (p1.x - p0.x) * localT,
      y: p0.y + (p1.y - p0.y) * localT,
      id: segments[i]!.id,
      type: segments[i]!.type,
      edgeName,
    });
  }

  return result;
}
