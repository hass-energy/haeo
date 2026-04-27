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
 */
function offsetPoints(points: Array<{ x: number; y: number }>, offset: number): Array<{ x: number; y: number }> {
  return points.map((p, i) => {
    const next = points[Math.min(i + 1, points.length - 1)]!;
    const prev = points[Math.max(i - 1, 0)]!;
    const dx = next.x - prev.x;
    const dy = next.y - prev.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len === 0) return { ...p };
    return { x: p.x + (dy / len) * offset, y: p.y - (dx / len) * offset };
  });
}

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
          {/* Per-VLAN arrow markers */}
          {[...activeVlans].map((tag) => (
            <marker
              key={`arrow-v${String(tag)}`}
              id={`arrow-v${String(tag)}`}
              markerWidth="8"
              markerHeight="6"
              refX="8"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill={vlanColor(tag)} />
            </marker>
          ))}
          {[...activeVlans].map((tag) => (
            <marker
              key={`arrow-rev-v${String(tag)}`}
              id={`arrow-rev-v${String(tag)}`}
              markerWidth="8"
              markerHeight="6"
              refX="0"
              refY="3"
              orient="auto"
            >
              <polygon points="8 0, 0 3, 8 6" fill={vlanColor(tag)} />
            </marker>
          ))}
        </defs>

        {/* Groups */}
        {layout.groups.map((group) => renderGroup(group, topology, setTooltip, hide))}

        {/* External edges — VLAN colored */}
        {layout.externalEdges.map((edge) => {
          const edgeName = edge.name.replace("ext:", "");
          const tags = edgeTags.get(edgeName);
          if (tags != null && tags.length > 0) {
            return renderVlanEdge(edge, tags);
          }
          return renderEdgePath(edge, "#888", true);
        })}

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
                        title: term.policyName,
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
      </svg>

      {/* VLAN Legend */}
      {activeVlans.size > 0 && (
        <div
          style={{
            position: "absolute",
            top: "8px",
            right: "8px",
            background: "rgba(30,30,30,0.9)",
            border: "1px solid #555",
            borderRadius: "6px",
            padding: "6px 10px",
            fontSize: "11px",
            color: "#eee",
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: "4px" }}>VLANs</div>
          {[...activeVlans].sort().map((tag) => (
            <div key={tag} style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "2px" }}>
              <div
                style={{
                  width: "16px",
                  height: "3px",
                  background: vlanColor(tag),
                  borderRadius: "1px",
                }}
              />
              <span>{tag === 0 ? "Default" : `VLAN ${String(tag)}`}</span>
            </div>
          ))}
        </div>
      )}

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
 * Render an edge with multiple VLAN colors as parallel offset stripes.
 */
function renderVlanEdge(edge: LayoutEdge, tags: number[]): JSX.Element | null {
  if (edge.points.length < 2) return null;
  const count = tags.length;
  const STRIPE_GAP = 2.5;

  return (
    <g key={edge.name}>
      {tags.map((tag, idx) => {
        const offset = count > 1 ? (idx - (count - 1) / 2) * STRIPE_GAP : 0;
        const pts = offset === 0 ? edge.points : offsetPoints(edge.points, offset);
        const d = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
        const color = vlanColor(tag);
        const markerId = edge.reversed ? `arrow-rev-v${String(tag)}` : `arrow-v${String(tag)}`;
        return (
          <path
            key={tag}
            d={d}
            fill="none"
            stroke={color}
            stroke-width="1.5"
            marker-end={!edge.reversed ? `url(#${markerId})` : undefined}
            marker-start={edge.reversed ? `url(#${markerId})` : undefined}
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

      {/* Internal edges (within group) */}
      {group.internalEdges.map((edge) => (
        <g key={edge.name} transform={`translate(${group.x},${group.y})`}>
          {renderEdgePathRaw(edge.points, "#ccc", false)}
        </g>
      ))}

      {/* Child nodes */}
      {group.children.map((child) =>
        child.isPill
          ? renderPill(child, group, setTooltip, hide)
          : renderModelNode(child, group, s?.color ?? "#bbb", topology, setTooltip, hide)
      )}

      {/* Ports */}
      {group.ports.map((port) => (
        <circle
          key={port.id}
          cx={group.x + port.x + port.width / 2}
          cy={group.y + port.y + port.height / 2}
          r={3}
          fill="#888"
        />
      ))}
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
      {/* VLAN outbound indicators — colored dots on left side (produces) */}
      {outTags
        .filter((t) => t !== 0)
        .map((tag, i) => (
          <circle
            key={`out-${String(tag)}`}
            cx={nx - 4}
            cy={ny + 8 + i * 10}
            r={4}
            fill={vlanColor(tag)}
            stroke="white"
            stroke-width="1"
          />
        ))}
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
        stroke="rgba(0,0,0,0.15)"
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
  const segs = node.segments;

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
