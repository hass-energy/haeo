/** ELK layout: groups as subgraphs with segments on internal edges. */

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
  side: "EAST" | "WEST";
}

export interface LayoutEdge {
  name: string;
  points: Array<{ x: number; y: number }>;
  internal: boolean;
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

const NODE_W = 130;
const NODE_H = 40;
const PILL_CELL_W = 28;
const PILL_H = 22;
const PORT_SZ = 8;
const PAD = 12;
const HDR = 22;

/**
 * Pre-layout: position groups as simple nodes to determine relative positions.
 * Returns a map: "groupA->groupB" => "EAST"|"WEST"|"NORTH"|"SOUTH"
 */
async function computePeerSides(elk: InstanceType<typeof ELK>, topology: TopologyData): Promise<Map<string, string>> {
  // Build simple undirected graph of groups
  const groupNames = Object.keys(topology.groups);
  const edgePairs = new Set<string>();

  for (const edge of topology.edges) {
    const sg = Object.entries(topology.groups).find(([, m]) => m.includes(edge.source))?.[0] ?? "";
    const tg = Object.entries(topology.groups).find(([, m]) => m.includes(edge.target))?.[0] ?? "";
    if (sg !== "" && tg !== "" && sg !== tg) {
      const key = [sg, tg].sort().join("--");
      edgePairs.add(key);
    }
  }

  const simpleGraph: ElkNode = {
    id: "pre",
    children: groupNames.map((name) => ({ id: name, width: 80, height: 40 })),
    edges: [...edgePairs].map((pair, i) => {
      const [a, b] = pair.split("--");
      return { id: `pe${String(i)}`, sources: [a ?? ""], targets: [b ?? ""] };
    }),
    layoutOptions: {
      "org.eclipse.elk.algorithm": "layered",
      "org.eclipse.elk.direction": "RIGHT",
      "org.eclipse.elk.randomSeed": "42",
    },
  };

  const result = await elk.layout(simpleGraph);
  const positions = new Map<string, { x: number; y: number }>();
  for (const child of result.children ?? []) {
    positions.set(child.id, {
      x: (child.x ?? 0) + (child.width ?? 80) / 2,
      y: (child.y ?? 0) + (child.height ?? 40) / 2,
    });
  }

  // For each pair of groups, determine which side of A faces B
  const sideMap = new Map<string, string>();
  for (const a of groupNames) {
    for (const b of groupNames) {
      if (a === b) continue;
      const posA = positions.get(a);
      const posB = positions.get(b);
      if (posA === undefined || posB === undefined) continue;

      const dx = posB.x - posA.x;
      const dy = posB.y - posA.y;

      let side: string;
      if (Math.abs(dx) >= Math.abs(dy)) {
        side = dx >= 0 ? "EAST" : "WEST";
      } else {
        side = dy >= 0 ? "SOUTH" : "NORTH";
      }
      sideMap.set(`${a}->${b}`, side);
    }
  }

  return sideMap;
}

export async function computeLayout(topology: TopologyData): Promise<LayoutResult> {
  const elk = new ELK();

  // Phase 1: Quick layout of just groups as simple nodes to determine
  // relative positions (which side of A faces B).
  const peerSides = await computePeerSides(elk, topology);

  const elkChildren: ElkNode[] = [];
  const elkEdges: ElkExtendedEdge[] = [];

  for (const [groupName, members] of Object.entries(topology.groups)) {
    const children: ElkNode[] = [];
    const internalEdges: ElkExtendedEdge[] = [];
    const ports: ElkPort[] = [];

    // Model element nodes
    for (const name of members) {
      children.push({ id: name, width: NODE_W, height: NODE_H });
    }

    // For each connection owned by this group (source is a member),
    // add a segment pill and internal edge: element → pill → out-port
    for (const edge of topology.edges) {
      const visible = edge.segments.filter((s) => s.type !== "PassthroughSegment");

      if (members.includes(edge.source)) {
        const targetGroup = Object.entries(topology.groups).find(([, m]) => m.includes(edge.target))?.[0] ?? "";
        const outSide = peerSides.get(`${groupName}->${targetGroup}`) ?? "EAST";
        ports.push({
          id: `port:${edge.name}:out`,
          width: PORT_SZ,
          height: PORT_SZ,
          layoutOptions: { "org.eclipse.elk.port.side": outSide },
        });

        if (visible.length > 0) {
          // Segment pill
          const pillId = `pill:${edge.name}`;
          children.push({
            id: pillId,
            width: visible.length * PILL_CELL_W + 8,
            height: PILL_H,
          });
          // element → pill
          internalEdges.push({
            id: `int:${edge.name}:a`,
            sources: [edge.source],
            targets: [pillId],
          });
          // pill → out-port
          internalEdges.push({
            id: `int:${edge.name}:b`,
            sources: [pillId],
            targets: [`port:${edge.name}:out`],
          });
        } else {
          // No segments — direct element → out-port
          internalEdges.push({
            id: `int:${edge.name}`,
            sources: [edge.source],
            targets: [`port:${edge.name}:out`],
          });
        }
      }

      if (members.includes(edge.target)) {
        const sourceGroup = Object.entries(topology.groups).find(([, m]) => m.includes(edge.source))?.[0] ?? "";
        const inSide = peerSides.get(`${groupName}->${sourceGroup}`) ?? "WEST";
        ports.push({
          id: `port:${edge.name}:in`,
          width: PORT_SZ,
          height: PORT_SZ,
          layoutOptions: { "org.eclipse.elk.port.side": inSide },
        });
        // in-port → element
        internalEdges.push({
          id: `int:${edge.name}:in`,
          sources: [`port:${edge.name}:in`],
          targets: [edge.target],
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
        "org.eclipse.elk.portConstraints": "FIXED_SIDE",
        "org.eclipse.elk.spacing.nodeNode": "15",
        "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "25",
      },
    });
  }

  // External edges between groups
  for (const edge of topology.edges) {
    elkEdges.push({
      id: `ext:${edge.name}`,
      sources: [`port:${edge.name}:out`],
      targets: [`port:${edge.name}:in`],
    });
  }

  const graph = await elk.layout({
    id: "root",
    children: elkChildren,
    edges: elkEdges,
    layoutOptions: {
      "org.eclipse.elk.algorithm": "layered",
      "org.eclipse.elk.direction": "RIGHT",
      "org.eclipse.elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "org.eclipse.elk.spacing.nodeNode": "30",
      "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "60",
      "org.eclipse.elk.portConstraints": "FIXED_SIDE",
      "org.eclipse.elk.randomSeed": "42",
    },
  });

  return extractResult(graph, topology);
}

function extractResult(graph: ElkNode, topology: TopologyData): LayoutResult {
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
      side: p.layoutOptions?.["org.eclipse.elk.port.side"] === "WEST" ? ("WEST" as const) : ("EAST" as const),
    }));

    const internalEdges: LayoutEdge[] = (child.edges ?? []).map((e) => {
      const sections = e.sections ?? [];
      const points: Array<{ x: number; y: number }> = [];
      for (const s of sections) {
        points.push(s.startPoint);
        for (const bp of s.bendPoints ?? []) points.push(bp);
        points.push(s.endPoint);
      }
      return { name: e.id, points, internal: true };
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
    const sections = e.sections ?? [];
    const points: Array<{ x: number; y: number }> = [];
    for (const s of sections) {
      points.push(s.startPoint);
      for (const bp of s.bendPoints ?? []) points.push(bp);
      points.push(s.endPoint);
    }
    return { name: e.id, points, internal: false };
  });

  return {
    groups,
    externalEdges,
    width: (graph.width ?? 800) + 20,
    height: (graph.height ?? 400) + 20,
  };
}
