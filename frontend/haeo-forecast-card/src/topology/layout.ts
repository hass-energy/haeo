/** ELK-based layout for HAEO network topology with ports and compound nodes. */

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
  label: string;
}

export interface LayoutEdge {
  name: string;
  source: string;
  target: string;
  sourcePort: string;
  targetPort: string;
  sections: Array<{
    startPoint: { x: number; y: number };
    endPoint: { x: number; y: number };
    bendPoints?: Array<{ x: number; y: number }> | undefined;
  }>;
  segments: Array<{
    id: string;
    type: string;
    x: number;
    y: number;
  }>;
}

export interface LayoutResult {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  width: number;
  height: number;
}

/** Element type to style mapping. */
export const NODE_STYLES: Record<string, { color: string; icon: string; label: string }> = {
  battery: { color: "#4CAF50", icon: "🔋", label: "Battery" },
  node: { color: "#90CAF9", icon: "⚡", label: "Node" },
  grid: { color: "#FF9800", icon: "🏭", label: "Grid" },
  solar: { color: "#FFD600", icon: "☀️", label: "Solar" },
  load: { color: "#E91E63", icon: "🏠", label: "Load" },
  inverter: { color: "#9C27B0", icon: "🔄", label: "Inverter" },
  network: { color: "#607D8B", icon: "📡", label: "System" },
  unknown: { color: "#BDBDBD", icon: "?", label: "Unknown" },
};

const SEGMENT_ICONS: Record<string, string> = {
  PricingSegment: "💲",
  PowerLimitSegment: "⚡",
  EfficiencySegment: "η",
  SocPricingSegment: "📊",
  TagFilterSegment: "🏷",
  TagPricingSegment: "🏷",
};

const NODE_MIN_WIDTH = 140;
const NODE_HEIGHT = 45;
const GROUP_PADDING = 15;
const PORT_SIZE = 10;
const SEGMENT_NODE_WIDTH = 70;
const SEGMENT_NODE_HEIGHT = 28;

function segmentLabel(seg: TopologySegment): string {
  const icon = SEGMENT_ICONS[seg.type] ?? "";
  const name = seg.type.replace("Segment", "");
  return `${icon} ${name}`.trim();
}

export async function computeLayout(topology: TopologyData): Promise<LayoutResult> {
  const elk = new ELK();

  // Build ELK graph: each element is a compound node containing its internal
  // structure. Connections become edges between ports on the compound nodes.
  const elkNodes: ElkNode[] = [];
  const elkEdges: ElkExtendedEdge[] = [];

  // Create compound node for each element group
  const groupNodes = new Map<string, ElkNode>();

  for (const [groupName, members] of Object.entries(topology.groups)) {
    // Child nodes within the group (the actual element nodes)
    const children: ElkNode[] = members.map((name) => ({
      id: name,
      width: NODE_MIN_WIDTH,
      height: NODE_HEIGHT,
      labels: [{ text: name }],
    }));

    // Ports for incoming/outgoing connections
    const inPorts: ElkPort[] = [];
    const outPorts: ElkPort[] = [];

    for (const edge of topology.edges) {
      if (members.includes(edge.target)) {
        inPorts.push({
          id: `port:${edge.name}:in`,
          width: PORT_SIZE,
          height: PORT_SIZE,
          layoutOptions: { "org.eclipse.elk.port.side": "WEST" },
        });

        // Add segment nodes inside the group for this incoming edge
        for (const seg of edge.segments.filter((s) => s.type !== "PassthroughSegment")) {
          children.push({
            id: `seg:${edge.name}:${seg.id}`,
            width: SEGMENT_NODE_WIDTH,
            height: SEGMENT_NODE_HEIGHT,
            labels: [{ text: segmentLabel(seg) }],
          });
        }
      }
      if (members.includes(edge.source)) {
        outPorts.push({
          id: `port:${edge.name}:out`,
          width: PORT_SIZE,
          height: PORT_SIZE,
          layoutOptions: { "org.eclipse.elk.port.side": "EAST" },
        });
      }
    }

    const groupNode: ElkNode = {
      id: `group:${groupName}`,
      labels: [{ text: groupName }],
      children,
      ports: [...inPorts, ...outPorts],
      layoutOptions: {
        "org.eclipse.elk.padding": `[top=${GROUP_PADDING + 20},left=${GROUP_PADDING},bottom=${GROUP_PADDING},right=${GROUP_PADDING}]`,
        "org.eclipse.elk.nodeLabels.placement": "H_LEFT V_TOP INSIDE",
      },
    };

    groupNodes.set(groupName, groupNode);
    elkNodes.push(groupNode);
  }

  // Create edges between group ports
  for (const edge of topology.edges) {
    const sourceGroup = findGroup(topology, edge.source);
    const targetGroup = findGroup(topology, edge.target);
    if (sourceGroup === undefined || targetGroup === undefined) continue;

    elkEdges.push({
      id: `edge:${edge.name}`,
      sources: [`group:${sourceGroup}`, `port:${edge.name}:out`],
      targets: [`group:${targetGroup}`, `port:${edge.name}:in`],
    });
  }

  const elkGraph: ElkNode = {
    id: "root",
    children: elkNodes,
    edges: elkEdges,
    layoutOptions: {
      "org.eclipse.elk.algorithm": "layered",
      "org.eclipse.elk.direction": "RIGHT",
      "org.eclipse.elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "org.eclipse.elk.spacing.nodeNode": "40",
      "org.eclipse.elk.spacing.edgeNode": "20",
      "org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers": "80",
      "org.eclipse.elk.portConstraints": "FIXED_SIDE",
      "org.eclipse.elk.randomSeed": "42",
    },
  };

  const layoutGraph = await elk.layout(elkGraph);

  // Extract results
  const nodes = extractNodes(layoutGraph, topology);
  const edges = extractEdges(layoutGraph, topology);

  return {
    nodes,
    edges,
    width: (layoutGraph.width ?? 800) + 40,
    height: (layoutGraph.height ?? 400) + 40,
  };
}

function findGroup(topology: TopologyData, nodeName: string): string | undefined {
  for (const [group, members] of Object.entries(topology.groups)) {
    if (members.includes(nodeName)) return group;
  }
  return undefined;
}

function extractNodes(graph: ElkNode, topology: TopologyData): LayoutNode[] {
  const result: LayoutNode[] = [];

  for (const child of graph.children ?? []) {
    if (!child.id.startsWith("group:")) continue;
    const groupName = child.id.slice(6);
    const groupType =
      topology.nodes.find((n) => topology.groups[groupName]?.includes(n.name) === true)?.type ?? "unknown";

    const children: LayoutNode[] = [];
    const ports: LayoutPort[] = [];

    for (const inner of child.children ?? []) {
      children.push({
        id: inner.id,
        x: inner.x ?? 0,
        y: inner.y ?? 0,
        width: inner.width ?? NODE_MIN_WIDTH,
        height: inner.height ?? NODE_HEIGHT,
        type: inner.id.startsWith("seg:") ? "segment" : groupType,
        isGroup: false,
        children: [],
        ports: [],
      });
    }

    for (const port of child.ports ?? []) {
      ports.push({
        id: port.id,
        x: port.x ?? 0,
        y: port.y ?? 0,
        width: port.width ?? PORT_SIZE,
        height: port.height ?? PORT_SIZE,
        side: port.layoutOptions?.["org.eclipse.elk.port.side"] === "WEST" ? "WEST" : "EAST",
        label: port.id,
      });
    }

    result.push({
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

  return result;
}

function extractEdges(graph: ElkNode, topology: TopologyData): LayoutEdge[] {
  const result: LayoutEdge[] = [];

  for (const edge of graph.edges ?? []) {
    const topoEdge = topology.edges.find((e) => `edge:${e.name}` === edge.id);
    if (!topoEdge) continue;

    const sections =
      edge.sections?.map((s) => ({
        startPoint: s.startPoint,
        endPoint: s.endPoint,
        bendPoints: s.bendPoints ?? undefined,
      })) ?? [];

    result.push({
      name: topoEdge.name,
      source: topoEdge.source,
      target: topoEdge.target,
      sourcePort: `port:${topoEdge.name}:out`,
      targetPort: `port:${topoEdge.name}:in`,
      sections,
      segments: [],
    });
  }

  return result;
}
