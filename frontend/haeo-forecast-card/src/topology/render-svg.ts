/**
 * Pure SVG string renderer for network topology.
 *
 * Mirrors the visual output of NetworkTopology.tsx but produces a plain
 * SVG string without requiring a DOM or Preact. Used by the headless
 * export script for scenario test visualizations.
 */

import {
  computeLayout,
  NODE_STYLES,
  type LayoutEdge,
  type LayoutGroup,
  type LayoutNode,
  type LayoutResult,
} from "./layout";
import {
  GROUP_RX,
  NODE_RX,
  PORT_EXTEND,
  SEGMENT_ICONS,
  STRIPE_GAP,
  type Point,
  computeArrowHead,
  esc,
  extendEndpoints,
  offsetPoints,
  vlanColor,
} from "./shared";
import type { TopologyData, TopologySegment } from "./types";

// ---------------------------------------------------------------------------
// SVG string helpers
// ---------------------------------------------------------------------------

function pathD(points: Point[]): string {
  return points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
}

function svgEdgePath(edge: LayoutEdge, color: string, arrow: boolean): string {
  if (edge.points.length < 2) return "";
  const d = pathD(edge.points);
  const markerEnd = arrow && !edge.reversed ? ' marker-end="url(#arrow)"' : "";
  const markerStart = arrow && edge.reversed ? ' marker-start="url(#arrow-rev)"' : "";
  return `<g><path d="${d}" fill="none" stroke="${color}" stroke-width="1.5"${markerEnd}${markerStart}/></g>`;
}

function svgEdgePathRaw(points: Point[], color: string, arrow: boolean): string {
  if (points.length < 2) return "";
  const d = pathD(points);
  const marker = arrow ? ' marker-end="url(#arrow)"' : "";
  return `<path d="${d}" fill="none" stroke="${color}" stroke-width="1.5"${marker}/>`;
}

function svgVlanStripes(points: Point[], tags: number[]): string {
  if (points.length < 2) return "";
  const count = tags.length;
  const parts: string[] = [];
  for (let idx = 0; idx < tags.length; idx++) {
    const tag = tags[idx]!;
    const offset = count > 1 ? (idx - (count - 1) / 2) * STRIPE_GAP : 0;
    const pts = offset === 0 ? points : offsetPoints(points, offset);
    const d = pathD(pts);
    parts.push(`<path d="${d}" fill="none" stroke="${vlanColor(tag)}" stroke-width="1.5"/>`);
  }
  return parts.join("");
}

function svgVlanEdge(edge: LayoutEdge, tags: number[]): string {
  if (edge.points.length < 2) return "";
  const count = tags.length;
  const extended = extendEndpoints(edge.points, PORT_EXTEND);
  const parts: string[] = [];
  for (let idx = 0; idx < tags.length; idx++) {
    const tag = tags[idx]!;
    const offset = count > 1 ? (idx - (count - 1) / 2) * STRIPE_GAP : 0;
    const pts = offset === 0 ? extended : offsetPoints(extended, offset);
    const d = pathD(pts);
    parts.push(`<path d="${d}" fill="none" stroke="${vlanColor(tag)}" stroke-width="1.5"/>`);
  }
  parts.push(svgCompositeArrow(edge.points, edge.reversed));
  return `<g>${parts.join("")}</g>`;
}

function svgCompositeArrow(points: Point[], reversed: boolean): string {
  const head = computeArrowHead(points, reversed);
  if (head == null) return "";
  const pts = `${head.tipX},${head.tipY} ${head.left.x},${head.left.y} ${head.right.x},${head.right.y}`;
  return `<polygon points="${pts}" fill="#888" stroke="white" stroke-width="1" stroke-linejoin="round"/>`;
}

// ---------------------------------------------------------------------------
// Node / pill / group renderers
// ---------------------------------------------------------------------------

function svgModelNode(node: LayoutNode, group: LayoutGroup, color: string, topology: TopologyData): string {
  const topoNode = topology.nodes.find((n) => n.name === node.id);
  const outTags = topoNode?.outbound_tags ?? [];
  const inTags = topoNode?.inbound_tags ?? [];
  const hasVlans = outTags.length > 0 || inTags.length > 0;
  const nx = group.x + node.x;
  const ny = group.y + node.y;
  const parts: string[] = [];

  if (hasVlans) {
    inTags
      .filter((t) => t !== 0)
      .forEach((tag, i) => {
        parts.push(
          `<circle cx="${nx + node.width + 4}" cy="${ny + 8 + i * 10}" r="4" fill="none" stroke="${vlanColor(tag)}" stroke-width="2"/>`
        );
      });
  }

  const stroke = outTags.length > 0 ? vlanColor(outTags.find((t) => t !== 0) ?? 0) : "rgba(0,0,0,0.15)";
  const strokeW = outTags.length > 0 ? "3" : "1";

  parts.push(
    `<rect x="${nx}" y="${ny}" width="${node.width}" height="${node.height}" rx="${NODE_RX}" fill="${color}" stroke="${stroke}" stroke-width="${strokeW}" opacity="0.85"/>`
  );
  parts.push(
    `<text x="${nx + node.width / 2}" y="${ny + node.height / 2 + 4}" text-anchor="middle" font-size="11" font-weight="600" fill="white">${esc(node.id)}</text>`
  );
  return `<g>${parts.join("")}</g>`;
}

function svgPill(node: LayoutNode, group: LayoutGroup): string {
  const px = group.x + node.x;
  const py = group.y + node.y;
  const cellW = 28;
  const segs = node.reversed ? [...node.segments].reverse() : node.segments;
  const parts: string[] = [];

  parts.push(
    `<rect x="${px}" y="${py}" width="${node.width}" height="${node.height}" rx="${node.height / 2}" fill="white" stroke="#bbb"/>`
  );

  segs.forEach((seg: TopologySegment, i: number) => {
    const sx = px + 4 + i * cellW + cellW / 2;
    const icon = SEGMENT_ICONS[seg.type] ?? "?";
    if (i > 0) {
      parts.push(
        `<line x1="${px + 4 + i * cellW}" y1="${py + 3}" x2="${px + 4 + i * cellW}" y2="${py + node.height - 3}" stroke="#ddd"/>`
      );
    }
    parts.push(`<text x="${sx}" y="${py + node.height / 2 + 4}" text-anchor="middle" font-size="12">${icon}</text>`);
  });

  return `<g>${parts.join("")}</g>`;
}

function svgGroup(group: LayoutGroup, topology: TopologyData, edgeTags: Map<string, number[]>): string {
  const s = NODE_STYLES[group.type] ?? NODE_STYLES["unknown"]!;
  const color = s.color;
  const icon = s.icon;
  const parts: string[] = [];

  // Group background
  parts.push(
    `<rect x="${group.x}" y="${group.y}" width="${group.width}" height="${group.height}" rx="${GROUP_RX}" fill="${color}12" stroke="${color}40" stroke-width="1.5"/>`
  );
  parts.push(
    `<text x="${group.x + 8}" y="${group.y + 14}" font-size="11" font-weight="700" fill="${color}">${icon} ${esc(group.id.replace("group:", ""))}</text>`
  );

  // Internal edges
  for (const edge of group.internalEdges) {
    const match = /^int:(.+?):[^:]+$/.exec(edge.name);
    const connName = match?.[1] ?? "";
    const tags = edgeTags.get(connName);
    if (tags != null && tags.length > 0) {
      parts.push(`<g transform="translate(${group.x},${group.y})">${svgVlanStripes(edge.points, tags)}</g>`);
    } else {
      parts.push(`<g transform="translate(${group.x},${group.y})">${svgEdgePathRaw(edge.points, "#ccc", false)}</g>`);
    }
  }

  // Child nodes
  for (const child of group.children) {
    if (child.isPill) {
      parts.push(svgPill(child, group));
    } else {
      parts.push(svgModelNode(child, group, color, topology));
    }
  }

  return `<g>${parts.join("")}</g>`;
}

function svgPolicyPill(pill: LayoutResult["policyPills"][number]): string {
  const parts: string[] = [];
  const cellW = 32;
  parts.push(
    `<rect x="${pill.x}" y="${pill.y}" width="${pill.width}" height="${pill.height}" rx="${pill.height / 2}" fill="white" stroke="#aaa" stroke-width="1.5"/>`
  );
  pill.terms.forEach((term, i) => {
    const color = vlanColor(term.tag);
    const cx = pill.x + 4 + i * cellW + cellW / 2;
    if (i > 0) {
      parts.push(
        `<line x1="${pill.x + 4 + i * cellW}" y1="${pill.y + 3}" x2="${pill.x + 4 + i * cellW}" y2="${pill.y + pill.height - 3}" stroke="#ddd"/>`
      );
    }
    parts.push(
      `<text x="${cx}" y="${pill.y + pill.height / 2 + 4}" text-anchor="middle" font-size="10" font-weight="700" fill="${color}">💲v${term.tag}</text>`
    );
  });
  return `<g>${parts.join("")}</g>`;
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

export async function renderTopologySvg(topology: TopologyData): Promise<string> {
  const layout = await computeLayout(topology);

  // Build edge name → tags lookup
  const edgeTags = new Map<string, number[]>();
  for (const edge of topology.edges) {
    if (edge.tags != null && edge.tags.length > 0) {
      edgeTags.set(edge.name, edge.tags);
    }
  }

  const activeVlans = new Set<number>();
  for (const tags of edgeTags.values()) {
    for (const t of tags) activeVlans.add(t);
  }

  const w = layout.width;
  const h = layout.height;
  const leg = layout.legend;

  const parts: string[] = [];

  // Defs
  parts.push("<defs>");
  parts.push(
    '<marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="#888"/></marker>'
  );
  parts.push(
    '<marker id="arrow-rev" markerWidth="8" markerHeight="6" refX="0" refY="3" orient="auto"><polygon points="8 0, 0 3, 8 6" fill="#888"/></marker>'
  );
  parts.push("</defs>");

  // Groups
  for (const group of layout.groups) {
    parts.push(svgGroup(group, topology, edgeTags));
  }

  // External edges
  for (const edge of layout.externalEdges) {
    const edgeName = edge.name.replace("ext:", "");
    const tags = edgeTags.get(edgeName);
    if (tags != null && tags.length > 0) {
      parts.push(svgVlanEdge(edge, tags));
    } else {
      parts.push(svgEdgePath(edge, "#888", true));
    }
  }

  // Port circles
  for (const group of layout.groups) {
    for (const port of group.ports) {
      parts.push(
        `<circle cx="${group.x + port.x + port.width / 2}" cy="${group.y + port.y + port.height / 2}" r="5" fill="#888"/>`
      );
    }
  }

  // Policy pricing pills
  for (const pill of layout.policyPills) {
    parts.push(svgPolicyPill(pill));
  }

  // VLAN legend
  if (leg != null && activeVlans.size > 0) {
    const legendParts: string[] = [];
    legendParts.push(
      `<rect x="${leg.x}" y="${leg.y}" width="${leg.width}" height="${leg.height}" rx="6" fill="rgba(30,30,30,0.9)" stroke="#555"/>`
    );
    legendParts.push(
      `<text x="${leg.x + 8}" y="${leg.y + 14}" font-size="11" font-weight="700" fill="#eee">VLANs</text>`
    );
    const sortedVlans = [...activeVlans].sort((a, b) => a - b);
    for (let i = 0; i < sortedVlans.length; i++) {
      const tag = sortedVlans[i]!;
      const label = tag === 0 ? "Default" : `VLAN ${tag}`;
      legendParts.push(
        `<rect x="${leg.x + 8}" y="${leg.y + 22 + i * 16}" width="16" height="3" rx="1" fill="${vlanColor(tag)}"/>`
      );
      legendParts.push(
        `<text x="${leg.x + 30}" y="${leg.y + 26 + i * 16}" font-size="10" fill="#ccc">${label}</text>`
      );
    }
    parts.push(`<g>${legendParts.join("")}</g>`);
  }

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">`,
    ...parts,
    "</svg>",
    "",
  ].join("\n");
}
