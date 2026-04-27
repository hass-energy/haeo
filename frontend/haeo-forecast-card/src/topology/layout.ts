/**
 * ELK layout with manual internal group positioning.
 *
 * Phase 1: Stress layout to determine group relative positions.
 * Phase 2: Manual internal layout — element node centered, pills placed
 *          on the side facing their port, with straight-line paths.
 * Phase 3: ELK stress layout of groups (as sized boxes) for final positions.
 * Phase 4: ELK routes external edges between groups.
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
const PAD = 16;
const HDR = 20;
const PILL_GAP = 6;
const PORT_GAP = 4;

type Side = "EAST" | "WEST" | "NORTH" | "SOUTH";

function findGroup(topology: TopologyData, nodeName: string): string {
  return Object.entries(topology.groups).find(([, m]) => m.includes(nodeName))?.[0] ?? "";
}

/**
 * Stress pre-layout to determine which side of each group faces each peer.
 */
async function computePeerSides(elk: InstanceType<typeof ELK>, topology: TopologyData): Promise<Map<string, Side>> {
  const groupNames = Object.keys(topology.groups);
  const edgePairs = new Set<string>();

  for (const edge of topology.edges) {
    const sg = findGroup(topology, edge.source);
    const tg = findGroup(topology, edge.target);
    if (sg !== "" && tg !== "" && sg !== tg) {
      edgePairs.add([sg, tg].sort().join("--"));
    }
  }

  const result = await elk.layout({
    id: "pre",
    children: groupNames.map((name) => ({ id: name, width: 80, height: 40 })),
    edges: [...edgePairs].map((pair, i) => {
      const [a, b] = pair.split("--");
      return { id: `pe${String(i)}`, sources: [a ?? ""], targets: [b ?? ""] };
    }),
    layoutOptions: {
      "org.eclipse.elk.algorithm": "stress",
      "org.eclipse.elk.randomSeed": "42",
      "org.eclipse.elk.stress.desiredEdgeLength": "150",
    },
  });

  const positions = new Map<string, { x: number; y: number }>();
  for (const child of result.children ?? []) {
    positions.set(child.id, {
      x: (child.x ?? 0) + child.width / 2,
      y: (child.y ?? 0) + child.height / 2,
    });
  }

  const sideMap = new Map<string, Side>();
  for (const a of groupNames) {
    for (const b of groupNames) {
      if (a === b) continue;
      const posA = positions.get(a);
      const posB = positions.get(b);
      if (posA === undefined || posB === undefined) continue;
      const dx = posB.x - posA.x;
      const dy = posB.y - posA.y;
      const side: Side = Math.abs(dx) >= Math.abs(dy) ? (dx >= 0 ? "EAST" : "WEST") : dy >= 0 ? "SOUTH" : "NORTH";
      sideMap.set(`${a}->${b}`, side);
    }
  }
  return sideMap;
}

interface PillInfo {
  id: string;
  edgeName: string;
  side: Side;
  segments: TopologySegment[];
  width: number;
  height: number;
  isOutgoing: boolean;
}

interface PortInfo {
  id: string;
  side: Side;
  edgeName: string;
  isOutgoing: boolean;
  pillId: string | null;
}

/**
 * Manually lay out a group's internals: element centered, pills on the
 * side facing their peer, ports at the edge, straight-line paths.
 */
function layoutGroupInternals(
  groupName: string,
  members: string[],
  topology: TopologyData,
  peerSides: Map<string, Side>
): { width: number; height: number; children: LayoutNode[]; ports: LayoutPort[]; edges: LayoutEdge[] } {
  const pills: PillInfo[] = [];
  const ports: PortInfo[] = [];

  // Collect pills and ports for connections
  for (const edge of topology.edges) {
    const visible = edge.segments.filter((s) => s.type !== "PassthroughSegment");

    if (members.includes(edge.source)) {
      const tg = findGroup(topology, edge.target);
      const side = peerSides.get(`${groupName}->${tg}`) ?? "EAST";
      const portId = `port:${edge.name}:out`;

      if (visible.length > 0) {
        const pillId = `pill:${edge.name}`;
        pills.push({
          id: pillId,
          edgeName: edge.name,
          side,
          segments: visible,
          width: visible.length * PILL_CELL_W + 8,
          height: PILL_H,
          isOutgoing: true,
        });
        ports.push({ id: portId, side, edgeName: edge.name, isOutgoing: true, pillId });
      } else {
        ports.push({ id: portId, side, edgeName: edge.name, isOutgoing: true, pillId: null });
      }
    }

    if (members.includes(edge.target)) {
      const sg = findGroup(topology, edge.source);
      const side = peerSides.get(`${groupName}->${sg}`) ?? "WEST";
      const portId = `port:${edge.name}:in`;
      ports.push({ id: portId, side, edgeName: edge.name, isOutgoing: false, pillId: null });
    }
  }

  // Group pills and ports by side
  const pillsBySide = new Map<Side, PillInfo[]>();
  const portsBySide = new Map<Side, PortInfo[]>();
  for (const s of ["NORTH", "SOUTH", "EAST", "WEST"] as Side[]) {
    pillsBySide.set(
      s,
      pills.filter((p) => p.side === s)
    );
    portsBySide.set(
      s,
      ports.filter((p) => p.side === s)
    );
  }

  // Calculate space needed on each side for pills
  const sideSpace = (side: Side): number => {
    const sidePills = pillsBySide.get(side) ?? [];
    if (sidePills.length === 0) return 0;
    if (side === "NORTH" || side === "SOUTH") {
      return PILL_H + PILL_GAP * 2;
    }
    return Math.max(...sidePills.map((p) => p.width)) + PILL_GAP * 2;
  };

  // Calculate the group box size
  const northSpace = sideSpace("NORTH");
  const southSpace = sideSpace("SOUTH");
  const westSpace = sideSpace("WEST");
  const eastSpace = sideSpace("EAST");

  // Minimum width/height to fit pills along each side
  const northPillsWidth = (pillsBySide.get("NORTH") ?? []).reduce((s, p) => s + p.width + PILL_GAP, 0);
  const southPillsWidth = (pillsBySide.get("SOUTH") ?? []).reduce((s, p) => s + p.width + PILL_GAP, 0);
  const westPillsHeight = (pillsBySide.get("WEST") ?? []).reduce((s, p) => s + p.height + PILL_GAP, 0);
  const eastPillsHeight = (pillsBySide.get("EAST") ?? []).reduce((s, p) => s + p.height + PILL_GAP, 0);

  const contentW = Math.max(NODE_W, northPillsWidth, southPillsWidth);
  const contentH = Math.max(NODE_H, westPillsHeight, eastPillsHeight);

  const totalW = PAD + westSpace + contentW + eastSpace + PAD;
  const totalH = HDR + PAD + northSpace + contentH + southSpace + PAD;

  // Position the model element node in the center
  const elemX = PAD + westSpace + (contentW - NODE_W) / 2;
  const elemY = HDR + PAD + northSpace + (contentH - NODE_H) / 2;

  const children: LayoutNode[] = members.map((name) => ({
    id: name,
    x: elemX,
    y: elemY,
    width: NODE_W,
    height: NODE_H,
    type: "element",
    isPill: false,
    segments: [],
    children: [],
    ports: [],
  }));

  const elemCx = elemX + NODE_W / 2;
  const elemCy = elemY + NODE_H / 2;

  // Position pills on their respective sides
  const positionedPills = new Map<string, { x: number; y: number; cx: number; cy: number }>();

  const placePills = (side: Side): void => {
    const sidePills = [...(pillsBySide.get(side) ?? [])];
    if (sidePills.length === 0) return;
    // Match port ordering: ascending by edge name, reversed on EAST only
    sidePills.sort((a, b) => a.edgeName.localeCompare(b.edgeName));
    if (side === "EAST") sidePills.reverse();

    if (side === "NORTH" || side === "SOUTH") {
      const totalPillW = sidePills.reduce((s, p) => s + p.width, 0) + (sidePills.length - 1) * PILL_GAP;
      let startX = PAD + westSpace + (contentW - totalPillW) / 2;
      const y =
        side === "NORTH"
          ? HDR + PAD + (northSpace - PILL_H) / 2
          : totalH - PAD - southSpace + (southSpace - PILL_H) / 2;

      for (const pill of sidePills) {
        positionedPills.set(pill.id, {
          x: startX,
          y,
          cx: startX + pill.width / 2,
          cy: y + pill.height / 2,
        });
        children.push({
          id: pill.id,
          x: startX,
          y,
          width: pill.width,
          height: pill.height,
          type: "pill",
          isPill: true,
          segments: pill.segments,
          children: [],
          ports: [],
        });
        startX += pill.width + PILL_GAP;
      }
    } else {
      const totalPillH = sidePills.reduce((s, p) => s + p.height, 0) + (sidePills.length - 1) * PILL_GAP;
      const x =
        side === "WEST"
          ? PAD + (westSpace - Math.max(...sidePills.map((p) => p.width))) / 2
          : totalW - PAD - eastSpace + (eastSpace - Math.max(...sidePills.map((p) => p.width))) / 2;
      let startY = HDR + PAD + northSpace + (contentH - totalPillH) / 2;

      for (const pill of sidePills) {
        positionedPills.set(pill.id, {
          x,
          y: startY,
          cx: x + pill.width / 2,
          cy: startY + pill.height / 2,
        });
        children.push({
          id: pill.id,
          x,
          y: startY,
          width: pill.width,
          height: pill.height,
          type: "pill",
          isPill: true,
          segments: pill.segments,
          children: [],
          ports: [],
        });
        startY += pill.height + PILL_GAP;
      }
    }
  };

  placePills("NORTH");
  placePills("SOUTH");
  placePills("EAST");
  placePills("WEST");

  // Position ports at the edge of the group box
  const layoutPorts: LayoutPort[] = [];
  const portPositions = new Map<string, { x: number; y: number }>();

  const placePortsOnSide = (side: Side): void => {
    const sidePorts = [...(portsBySide.get(side) ?? [])];
    if (sidePorts.length === 0) return;

    // Sort by edge name. Reverse on EAST (not WEST) so that counter-flowing
    // bidirectional edges between WEST↔EAST groups run parallel without crossing.
    // NORTH↔SOUTH groups keep the same order on both sides.
    sidePorts.sort((a, b) => a.edgeName.localeCompare(b.edgeName));
    if (side === "EAST") sidePorts.reverse();

    if (side === "NORTH" || side === "SOUTH") {
      const totalPortW = sidePorts.length * PORT_SZ + (sidePorts.length - 1) * PORT_GAP;
      let startX = PAD + westSpace + (contentW - totalPortW) / 2;
      const y = side === "NORTH" ? -PORT_SZ / 2 : totalH - PORT_SZ / 2;

      for (const port of sidePorts) {
        // If this port has a pill, place it near the pill
        const pill = port.pillId != null ? positionedPills.get(port.pillId) : null;
        const px = pill != null ? pill.cx - PORT_SZ / 2 : startX;
        layoutPorts.push({ id: port.id, x: px, y, width: PORT_SZ, height: PORT_SZ, side });
        portPositions.set(port.id, { x: px + PORT_SZ / 2, y: y + PORT_SZ / 2 });
        startX += PORT_SZ + PORT_GAP;
      }
    } else {
      const totalPortH = sidePorts.length * PORT_SZ + (sidePorts.length - 1) * PORT_GAP;
      let startY = HDR + PAD + northSpace + (contentH - totalPortH) / 2;
      const x = side === "WEST" ? -PORT_SZ / 2 : totalW - PORT_SZ / 2;

      for (const port of sidePorts) {
        const pill = port.pillId != null ? positionedPills.get(port.pillId) : null;
        const py = pill != null ? pill.cy - PORT_SZ / 2 : startY;
        layoutPorts.push({ id: port.id, x, y: py, width: PORT_SZ, height: PORT_SZ, side });
        portPositions.set(port.id, { x: x + PORT_SZ / 2, y: py + PORT_SZ / 2 });
        startY += PORT_SZ + PORT_GAP;
      }
    }
  };

  placePortsOnSide("NORTH");
  placePortsOnSide("SOUTH");
  placePortsOnSide("EAST");
  placePortsOnSide("WEST");

  // Build straight-line internal edges
  const edges: LayoutEdge[] = [];

  for (const port of ports) {
    const portPos = portPositions.get(port.id);
    if (portPos === undefined) continue;

    const pill = port.pillId != null ? positionedPills.get(port.pillId) : null;

    if (port.isOutgoing && pill != null) {
      // Element → pill → port (two straight segments)
      edges.push({
        name: `int:${port.edgeName}:a`,
        points: [
          { x: elemCx, y: elemCy },
          { x: pill.cx, y: pill.cy },
        ],
        internal: true,
      });
      edges.push({
        name: `int:${port.edgeName}:b`,
        points: [{ x: pill.cx, y: pill.cy }, portPos],
        internal: true,
      });
    } else if (port.isOutgoing) {
      // Element → port (straight line)
      edges.push({
        name: `int:${port.edgeName}`,
        points: [{ x: elemCx, y: elemCy }, portPos],
        internal: true,
      });
    } else {
      // Port → element (incoming, straight line)
      edges.push({
        name: `int:${port.edgeName}:in`,
        points: [portPos, { x: elemCx, y: elemCy }],
        internal: true,
      });
    }
  }

  return { width: totalW, height: totalH, children, ports: layoutPorts, edges };
}

export async function computeLayout(topology: TopologyData): Promise<LayoutResult> {
  const elk = new ELK();
  const peerSides = await computePeerSides(elk, topology);

  // Lay out each group's internals to get their sizes
  const groupInternals = new Map<string, ReturnType<typeof layoutGroupInternals>>();
  const elkChildren: ElkNode[] = [];

  for (const [groupName, members] of Object.entries(topology.groups)) {
    const internal = layoutGroupInternals(groupName, members, topology, peerSides);
    groupInternals.set(groupName, internal);

    // Build ELK ports for the outer layout
    const elkPorts: ElkPort[] = internal.ports.map((p) => ({
      id: p.id,
      x: p.x,
      y: p.y,
      width: p.width,
      height: p.height,
      layoutOptions: { "org.eclipse.elk.port.side": p.side },
    }));

    elkChildren.push({
      id: `group:${groupName}`,
      width: internal.width,
      height: internal.height,
      ports: elkPorts,
      layoutOptions: {
        "org.eclipse.elk.portConstraints": "FIXED_POS",
      },
    });
  }

  // External edges
  const elkEdges: ElkExtendedEdge[] = topology.edges.map((edge) => ({
    id: `ext:${edge.name}`,
    sources: [`port:${edge.name}:out`],
    targets: [`port:${edge.name}:in`],
  }));

  const graph: ElkNode = await elk.layout({
    id: "root",
    children: elkChildren,
    edges: elkEdges,
    layoutOptions: {
      "org.eclipse.elk.algorithm": "stress",
      "org.eclipse.elk.randomSeed": "42",
      "org.eclipse.elk.stress.desiredEdgeLength": "300",
      "org.eclipse.elk.portConstraints": "FIXED_POS",
    },
  });

  // Assemble final result
  const groups: LayoutGroup[] = [];
  for (const child of graph.children ?? []) {
    const groupName = child.id.replace("group:", "");
    const internal = groupInternals.get(groupName);
    if (internal === undefined) continue;

    const gType = topology.nodes.find((n) => topology.groups[groupName]?.includes(n.name) === true)?.type ?? "unknown";

    groups.push({
      id: child.id,
      type: gType,
      x: child.x ?? 0,
      y: child.y ?? 0,
      width: child.width ?? internal.width,
      height: child.height ?? internal.height,
      children: internal.children,
      ports: internal.ports,
      internalEdges: internal.edges,
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
