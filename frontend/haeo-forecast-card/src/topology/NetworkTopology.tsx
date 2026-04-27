/** Network topology SVG component. */

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
        </defs>

        {/* Groups */}
        {layout.groups.map((group) => renderGroup(group, setTooltip, hide))}

        {/* External edges between groups */}
        {layout.externalEdges.map((edge) => renderEdgePath(edge, "#666", true))}
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

function renderGroup(group: LayoutGroup, setTooltip: (t: TooltipInfo) => void, hide: () => void): JSX.Element {
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
          : renderModelNode(child, group, s?.color ?? "#bbb", setTooltip, hide)
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
  setTooltip: (t: TooltipInfo) => void,
  hide: () => void
): JSX.Element {
  return (
    <g
      key={node.id}
      onMouseEnter={(e: MouseEvent) =>
        setTooltip({ x: e.clientX, y: e.clientY, title: node.id, lines: [`Type: ${node.type}`] })
      }
      onMouseLeave={hide}
      style={{ cursor: "pointer" }}
    >
      <rect
        x={group.x + node.x}
        y={group.y + node.y}
        width={node.width}
        height={node.height}
        rx={NODE_RX}
        fill={color}
        stroke="rgba(0,0,0,0.15)"
        opacity="0.85"
      />
      <text
        x={group.x + node.x + node.width / 2}
        y={group.y + node.y + node.height / 2 + 4}
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
  return <g key={edge.name}>{renderEdgePathRaw(edge.points, color, arrow)}</g>;
}

function renderEdgePathRaw(points: Array<{ x: number; y: number }>, color: string, arrow: boolean): JSX.Element | null {
  if (points.length < 2) return null;
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  return <path d={d} fill="none" stroke={color} stroke-width="1.5" marker-end={arrow ? "url(#arrow)" : undefined} />;
}
