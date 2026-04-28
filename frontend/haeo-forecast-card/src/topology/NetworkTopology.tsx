/** Network topology SVG component with VLAN coloring. */

import type { JSX } from "preact";
import { useEffect, useState } from "preact/hooks";
import {
  computeLayout,
  NODE_STYLES,
  type LayoutEdge,
  type LayoutGroup,
  type LayoutNode,
  type LayoutResult,
} from "./layout";
import type { TopologyData, TopologySegment } from "./types";

const NODE_RX = 6;
const GROUP_RX = 10;

const SEGMENT_ICONS: Record<string, string> = {
  PricingSegment: "💲",
  PowerLimitSegment: "⚡",
  EfficiencySegment: "η",
  SocPricingSegment: "📊",
  TagFilterSegment: "🏷",
  TagPricingSegment: "🏷",
};

/** Distinct colors for VLAN tags. Tag 0 (default) is neutral gray. */
const VLAN_COLORS: string[] = [
  "#888", // tag 0 — default/untagged
  "#E91E63", // tag 1 — pink
  "#2196F3", // tag 2 — blue
  "#4CAF50", // tag 3 — green
  "#FF9800", // tag 4 — orange
  "#9C27B0", // tag 5 — purple
  "#00BCD4", // tag 6 — cyan
  "#CDDC39", // tag 7 — lime
];

function vlanColor(tag: number): string {
  return VLAN_COLORS[tag % VLAN_COLORS.length] ?? "#888";
}

/**
 * Offset a polyline perpendicular to each segment direction.
 *
 * For each line segment, compute an independent perpendicular offset.
 * At corners where two segments meet, find the intersection of the two
 * offset lines (miter join) so parallel lines stay truly parallel through
 * orthogonal bends.
 */
function offsetPoints(points: Array<{ x: number; y: number }>, offset: number): Array<{ x: number; y: number }> {
  if (points.length < 2) return points.map((p) => ({ ...p }));

  // Compute per-segment perpendicular normals
  const normals: Array<{ nx: number; ny: number }> = [];
  for (let i = 0; i < points.length - 1; i++) {
    const dx = points[i + 1]!.x - points[i]!.x;
    const dy = points[i + 1]!.y - points[i]!.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len === 0) {
      normals.push({ nx: 0, ny: 0 });
    } else {
      normals.push({ nx: dy / len, ny: -dx / len });
    }
  }

  const result: Array<{ x: number; y: number }> = [];
  for (let i = 0; i < points.length; i++) {
    const p = points[i]!;
    if (i === 0) {
      // First point: offset along first segment's normal
      const n = normals[0]!;
      result.push({ x: p.x + n.nx * offset, y: p.y + n.ny * offset });
    } else if (i === points.length - 1) {
      // Last point: offset along last segment's normal
      const n = normals[normals.length - 1]!;
      result.push({ x: p.x + n.nx * offset, y: p.y + n.ny * offset });
    } else {
      // Interior point: intersect the offset lines of adjacent segments
      const nA = normals[i - 1]!;
      const nB = normals[i]!;

      // Offset lines: pA + t * dA and pB + s * dB
      // where pA/pB are offset points on each segment, dA/dB are segment directions
      const pA = points[i - 1]!;
      const pB = points[i + 1]!;
      const dAx = p.x - pA.x;
      const dAy = p.y - pA.y;
      const dBx = pB.x - p.x;
      const dBy = pB.y - p.y;

      // Cross product of directions to check if segments are parallel
      const cross = dAx * dBy - dAy * dBx;
      if (Math.abs(cross) < 1e-6) {
        // Parallel segments — just use the normal
        result.push({ x: p.x + nA.nx * offset, y: p.y + nA.ny * offset });
      } else {
        // Find intersection of the two offset lines
        const oAx = pA.x + nA.nx * offset;
        const oAy = pA.y + nA.ny * offset;
        const oBx = p.x + nB.nx * offset;
        const oBy = p.y + nB.ny * offset;

        // Line A: oA + t * dA = intersection
        // Line B: oB + s * dB = intersection
        // Solve: oAx + t*dAx = oBx + s*dBx
        //        oAy + t*dAy = oBy + s*dBy
        const t = ((oBx - oAx) * dBy - (oBy - oAy) * dBx) / cross;
        result.push({ x: oAx + t * dAx, y: oAy + t * dAy });
      }
    }
  }
  return result;
}

/** Extend a polyline's first and last points outward along their segments. */
function extendEndpoints(points: Array<{ x: number; y: number }>, dist: number): Array<{ x: number; y: number }> {
  if (points.length < 2) return points;
  const result = points.map((p) => ({ ...p }));
  // Extend start outward
  const dx0 = result[0]!.x - result[1]!.x;
  const dy0 = result[0]!.y - result[1]!.y;
  const len0 = Math.sqrt(dx0 * dx0 + dy0 * dy0);
  if (len0 > 0) {
    result[0] = { x: result[0]!.x + (dx0 / len0) * dist, y: result[0]!.y + (dy0 / len0) * dist };
  }
  // Extend end outward
  const last = result.length - 1;
  const dx1 = result[last]!.x - result[last - 1]!.x;
  const dy1 = result[last]!.y - result[last - 1]!.y;
  const len1 = Math.sqrt(dx1 * dx1 + dy1 * dy1);
  if (len1 > 0) {
    result[last] = { x: result[last]!.x + (dx1 / len1) * dist, y: result[last]!.y + (dy1 / len1) * dist };
  }
  return result;
}

/** Distance to extend VLAN lines into port circles (half of PORT_SZ in layout). */
const PORT_EXTEND = 6;

/** Arrow head dimensions. */
const ARROW_LEN = 10;
const ARROW_HALF_W = 5;

interface TooltipInfo {
  x: number;
  y: number;
  title: string;
  lines: string[];
}

interface Props {
  topology: TopologyData;
  width?: number;
  height?: number;
}

export function NetworkTopology(props: Props): JSX.Element {
  const { topology } = props;
  const [layout, setLayout] = useState<LayoutResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  useEffect(() => {
    void computeLayout(topology)
      .then(setLayout)
      .catch((e: unknown) => setError(String(e)));
  }, [topology]);

  if (error != null) return <div style={{ color: "red" }}>Layout error: {error}</div>;
  if (layout == null) return <div>Computing layout…</div>;

  // Build edge name → tags lookup
  const edgeTags = new Map<string, number[]>();
  for (const edge of topology.edges) {
    if (edge.tags != null && edge.tags.length > 0) {
      edgeTags.set(edge.name, edge.tags);
    }
  }

  // Collect all active VLAN IDs for the legend
  const activeVlans = new Set<number>();
  for (const tags of edgeTags.values()) {
    for (const t of tags) activeVlans.add(t);
  }

  const leg = layout.legend;
  const w = props.width ?? layout.width;
  const h = props.height ?? layout.height;
  const hide = (): void => setTooltip(null);

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${w} ${h}`} width={w} height={h}>
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#888" />
          </marker>
          <marker id="arrow-rev" markerWidth="8" markerHeight="6" refX="0" refY="3" orient="auto">
            <polygon points="8 0, 0 3, 8 6" fill="#888" />
          </marker>
        </defs>

        {/* Groups */}
        {layout.groups.map((group) => renderGroup(group, topology, edgeTags, setTooltip, hide))}

        {/* External edges — VLAN colored */}
        {layout.externalEdges.map((edge) => {
          const edgeName = edge.name.replace("ext:", "");
          const tags = edgeTags.get(edgeName);
          if (tags != null && tags.length > 0) {
            return renderVlanEdge(edge, tags);
          }
          return renderEdgePath(edge, "#888", true);
        })}

        {/* Port circles — rendered after edges so they sit on top */}
        {layout.groups.map((group) =>
          group.ports.map((port) => (
            <circle
              key={port.id}
              cx={group.x + port.x + port.width / 2}
              cy={group.y + port.y + port.height / 2}
              r={5}
              fill="#888"
            />
          ))
        )}

        {/* Policy pricing pills (positioned by ELK) */}
        {layout.policyPills.map((pill) => {
          const terms = pill.terms;
          const pillW = pill.width;
          const pillH = pill.height;
          const cellW = 32;
          return (
            <g key={pill.id}>
              <rect
                x={pill.x}
                y={pill.y}
                width={pillW}
                height={pillH}
                rx={pillH / 2}
                fill="white"
                stroke="#aaa"
                stroke-width="1.5"
              />
              {terms.map((term, i) => {
                const color = vlanColor(term.tag);
                const cx = pill.x + 4 + i * cellW + cellW / 2;
                return (
                  <g
                    key={`${term.policyName}-${String(term.tag)}`}
                    onMouseEnter={(e: MouseEvent) =>
                      setTooltip({
                        x: e.clientX,
                        y: e.clientY,
                        title: term.policyLabel,
                        lines: [`VLAN ${String(term.tag)}`, `Edge: ${pill.connectionName}`],
                      })
                    }
                    onMouseLeave={hide}
                    style={{ cursor: "pointer" }}
                  >
                    {i > 0 && (
                      <line
                        x1={pill.x + 4 + i * cellW}
                        y1={pill.y + 3}
                        x2={pill.x + 4 + i * cellW}
                        y2={pill.y + pillH - 3}
                        stroke="#ddd"
                      />
                    )}
                    <text
                      x={cx}
                      y={pill.y + pillH / 2 + 4}
                      text-anchor="middle"
                      font-size="10"
                      font-weight="700"
                      fill={color}
                    >
                      💲v{String(term.tag)}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
        {/* VLAN Legend (positioned by ELK) */}
        {leg != null && activeVlans.size > 0 && (
          <g>
            <rect
              x={leg.x}
              y={leg.y}
              width={leg.width}
              height={leg.height}
              rx={6}
              fill="rgba(30,30,30,0.9)"
              stroke="#555"
            />
            <text x={leg.x + 8} y={leg.y + 14} font-size="11" font-weight="700" fill="#eee">
              VLANs
            </text>
            {[...activeVlans].sort().map((tag, i) => (
              <g key={tag}>
                <rect x={leg.x + 8} y={leg.y + 22 + i * 16} width={16} height={3} rx={1} fill={vlanColor(tag)} />
                <text x={leg.x + 30} y={leg.y + 26 + i * 16} font-size="10" fill="#ccc">
                  {tag === 0 ? "Default" : `VLAN ${String(tag)}`}
                </text>
              </g>
            ))}
          </g>
        )}
      </svg>

      {/* Tooltip */}
      {tooltip != null && (
        <div
          style={{
            position: "fixed",
            left: `${tooltip.x + 12}px`,
            top: `${tooltip.y - 10}px`,
            background: "rgba(30,30,30,0.95)",
            color: "white",
            padding: "8px 12px",
            borderRadius: "6px",
            fontSize: "12px",
            zIndex: 1000,
            pointerEvents: "none",
            boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
            maxWidth: "250px",
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: "4px" }}>{tooltip.title}</div>
          {tooltip.lines.map((line, i) => (
            <div key={i} style={{ opacity: 0.8 }}>
              {line}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Render parallel VLAN-colored stripes for a set of points (no arrows).
 * Extends endpoints so lines reach into port circles.
 */
function renderVlanStripes(points: Array<{ x: number; y: number }>, tags: number[]): JSX.Element | null {
  if (points.length < 2) return null;
  const count = tags.length;
  const STRIPE_GAP = 2.5;

  return (
    <>
      {tags.map((tag, idx) => {
        const offset = count > 1 ? (idx - (count - 1) / 2) * STRIPE_GAP : 0;
        const pts = offset === 0 ? points : offsetPoints(points, offset);
        const d = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
        return <path key={tag} d={d} fill="none" stroke={vlanColor(tag)} stroke-width="1.5" />;
      })}
    </>
  );
}

/**
 * Render an edge with multiple VLAN colors as parallel offset stripes.
 * Lines extend into port circles; a single composite arrow head shows direction.
 */
function renderVlanEdge(edge: LayoutEdge, tags: number[]): JSX.Element | null {
  if (edge.points.length < 2) return null;
  const count = tags.length;
  const STRIPE_GAP = 2.5;
  const extended = extendEndpoints(edge.points, PORT_EXTEND);

  return (
    <g key={edge.name}>
      {tags.map((tag, idx) => {
        const offset = count > 1 ? (idx - (count - 1) / 2) * STRIPE_GAP : 0;
        const pts = offset === 0 ? extended : offsetPoints(extended, offset);
        const d = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
        return <path key={tag} d={d} fill="none" stroke={vlanColor(tag)} stroke-width="1.5" />;
      })}
      {renderCompositeArrow(edge.points, tags, edge.reversed, edge.name)}
    </g>
  );
}

/**
 * Render a single arrow head with equal VLAN-colored slices.
 * Each VLAN gets a geometric polygon slice so color boundaries are clean.
 */
function renderCompositeArrow(
  points: Array<{ x: number; y: number }>,
  tags: number[],
  reversed: boolean,
  _edgeName: string
): JSX.Element | null {
  if (points.length < 2) return null;

  const tipIdx = reversed ? 0 : points.length - 1;
  const prevIdx = reversed ? 1 : points.length - 2;
  const tip = points[tipIdx]!;
  const prev = points[prevIdx]!;

  const dx = tip.x - prev.x;
  const dy = tip.y - prev.y;
  const len = Math.sqrt(dx * dx + dy * dy);
  if (len === 0) return null;

  const ux = dx / len;
  const uy = dy / len;
  const px = -uy;
  const py = ux;

  const baseX = tip.x - ux * ARROW_LEN;
  const baseY = tip.y - uy * ARROW_LEN;
  const left = { x: baseX + px * ARROW_HALF_W, y: baseY + py * ARROW_HALF_W };
  const right = { x: baseX - px * ARROW_HALF_W, y: baseY - py * ARROW_HALF_W };

  if (tags.length === 1) {
    return (
      <polygon
        points={`${tip.x},${tip.y} ${left.x},${left.y} ${right.x},${right.y}`}
        fill={vlanColor(tags[0]!)}
      />
    );
  }

  // Slice the triangle into N bands perpendicular to the base.
  // When reversed, flip the slice order to match stripe offset direction.
  const n = tags.length;
  const orderedTags = reversed ? [...tags].reverse() : tags;

  return (
    <g>
      {orderedTags.map((tag, i) => {
        const t0 = i / n;
        const t1 = (i + 1) / n;
        // Slice runs between two cuts across the triangle. Each cut at
        // fraction t goes from the left→tip edge to the right→tip edge.
        const l0 = { x: left.x + (tip.x - left.x) * t0, y: left.y + (tip.y - left.y) * t0 };
        const l1 = { x: left.x + (tip.x - left.x) * t1, y: left.y + (tip.y - left.y) * t1 };
        const r0 = { x: right.x + (tip.x - right.x) * t0, y: right.y + (tip.y - right.y) * t0 };
        const r1 = { x: right.x + (tip.x - right.x) * t1, y: right.y + (tip.y - right.y) * t1 };
        return (
          <polygon
            key={tag}
            points={`${l0.x},${l0.y} ${r0.x},${r0.y} ${r1.x},${r1.y} ${l1.x},${l1.y}`}
            fill={vlanColor(tag)}
          />
        );
      })}
    </g>
  );
}

/**
 * Render a policy pricing pill on a min-cut edge.
 * Positioned at the midpoint of the edge, offset vertically when
 * multiple policies share the same connection.
 */
function renderGroup(
  group: LayoutGroup,
  topology: TopologyData,
  edgeTags: Map<string, number[]>,
  setTooltip: (t: TooltipInfo) => void,
  hide: () => void
): JSX.Element {
  const s = NODE_STYLES[group.type] ?? NODE_STYLES["unknown"];

  return (
    <g key={group.id}>
      {/* Group background */}
      <rect
        x={group.x}
        y={group.y}
        width={group.width}
        height={group.height}
        rx={GROUP_RX}
        fill={`${s?.color ?? "#bbb"}12`}
        stroke={`${s?.color ?? "#bbb"}40`}
        stroke-width="1.5"
      />
      <text x={group.x + 8} y={group.y + 14} font-size="11" font-weight="700" fill={s?.color ?? "#666"}>
        {s?.icon ?? "?"} {group.id.replace("group:", "")}
      </text>

      {/* Internal edges (within group) — VLAN colored when tagged */}
      {group.internalEdges.map((edge) => {
        // Extract connection name: int:{edgeName}:{suffix}
        const match = /^int:(.+?):[^:]+$/.exec(edge.name);
        const connName = match?.[1] ?? "";
        const tags = edgeTags.get(connName);
        if (tags != null && tags.length > 0) {
          return (
            <g key={edge.name} transform={`translate(${group.x},${group.y})`}>
              {renderVlanStripes(edge.points, tags)}
            </g>
          );
        }
        return (
          <g key={edge.name} transform={`translate(${group.x},${group.y})`}>
            {renderEdgePathRaw(edge.points, "#ccc", false)}
          </g>
        );
      })}

      {/* Child nodes */}
      {group.children.map((child) =>
        child.isPill
          ? renderPill(child, group, setTooltip, hide)
          : renderModelNode(child, group, s?.color ?? "#bbb", topology, setTooltip, hide)
      )}
    </g>
  );
}

function renderModelNode(
  node: LayoutNode,
  group: LayoutGroup,
  color: string,
  topology: TopologyData,
  setTooltip: (t: TooltipInfo) => void,
  hide: () => void
): JSX.Element {
  const topoNode = topology.nodes.find((n) => n.name === node.id);
  const outTags = topoNode?.outbound_tags ?? [];
  const inTags = topoNode?.inbound_tags ?? [];
  const hasVlans = outTags.length > 0 || inTags.length > 0;

  const nx = group.x + node.x;
  const ny = group.y + node.y;
  const tooltipLines = [`Type: ${node.type}`];
  if (outTags.length > 0)
    tooltipLines.push(`Produces: ${outTags.map((t) => (t === 0 ? "default" : `VLAN ${String(t)}`)).join(", ")}`);
  if (inTags.length > 0)
    tooltipLines.push(`Accepts: ${inTags.map((t) => (t === 0 ? "default" : `VLAN ${String(t)}`)).join(", ")}`);

  return (
    <g
      key={node.id}
      onMouseEnter={(e: MouseEvent) => setTooltip({ x: e.clientX, y: e.clientY, title: node.id, lines: tooltipLines })}
      onMouseLeave={hide}
      style={{ cursor: "pointer" }}
    >
      {/* VLAN inbound indicators — colored dots on right side (accepts) */}
      {hasVlans &&
        inTags
          .filter((t) => t !== 0)
          .map((tag, i) => (
            <circle
              key={`in-${String(tag)}`}
              cx={nx + node.width + 4}
              cy={ny + 8 + i * 10}
              r={4}
              fill="none"
              stroke={vlanColor(tag)}
              stroke-width="2"
            />
          ))}
      <rect
        x={nx}
        y={ny}
        width={node.width}
        height={node.height}
        rx={NODE_RX}
        fill={color}
        stroke={
          outTags.length > 0 ? vlanColor(outTags.find((t) => t !== 0) ?? 0) : "rgba(0,0,0,0.15)"
        }
        stroke-width={outTags.length > 0 ? "3" : "1"}
        opacity="0.85"
      />
      <text
        x={nx + node.width / 2}
        y={ny + node.height / 2 + 4}
        text-anchor="middle"
        font-size="11"
        font-weight="600"
        fill="white"
      >
        {node.id}
      </text>
    </g>
  );
}

function renderPill(
  node: LayoutNode,
  group: LayoutGroup,
  setTooltip: (t: TooltipInfo) => void,
  hide: () => void
): JSX.Element {
  const px = group.x + node.x;
  const py = group.y + node.y;
  const cellW = 28;
  // Reverse segment order when the edge was flipped for layout so pills
  // read in the visual flow direction (left-to-right).
  const segs = node.reversed ? [...node.segments].reverse() : node.segments;

  return (
    <g key={node.id}>
      <rect x={px} y={py} width={node.width} height={node.height} rx={node.height / 2} fill="white" stroke="#bbb" />
      {segs.map((seg: TopologySegment, i: number) => {
        const sx = px + 4 + i * cellW + cellW / 2;
        const icon = SEGMENT_ICONS[seg.type] ?? "?";
        return (
          <g
            key={seg.id}
            onMouseEnter={(e: MouseEvent) =>
              setTooltip({
                x: e.clientX,
                y: e.clientY,
                title: seg.id,
                lines: [seg.type.replace("Segment", ""), node.id.replace("pill:", "")],
              })
            }
            onMouseLeave={hide}
            style={{ cursor: "pointer" }}
          >
            {i > 0 && (
              <line
                x1={px + 4 + i * cellW}
                y1={py + 3}
                x2={px + 4 + i * cellW}
                y2={py + node.height - 3}
                stroke="#ddd"
              />
            )}
            <text x={sx} y={py + node.height / 2 + 4} text-anchor="middle" font-size="12">
              {icon}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function renderEdgePath(edge: LayoutEdge, color: string, arrow: boolean): JSX.Element | null {
  if (edge.points.length < 2) return null;
  const d = edge.points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const markerEnd = arrow && !edge.reversed ? "url(#arrow)" : undefined;
  const markerStart = arrow && edge.reversed ? "url(#arrow-rev)" : undefined;
  return (
    <g key={edge.name}>
      <path d={d} fill="none" stroke={color} stroke-width="1.5" marker-end={markerEnd} marker-start={markerStart} />
    </g>
  );
}

function renderEdgePathRaw(points: Array<{ x: number; y: number }>, color: string, arrow: boolean): JSX.Element | null {
  if (points.length < 2) return null;
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  return <path d={d} fill="none" stroke={color} stroke-width="1.5" marker-end={arrow ? "url(#arrow)" : undefined} />;
}
