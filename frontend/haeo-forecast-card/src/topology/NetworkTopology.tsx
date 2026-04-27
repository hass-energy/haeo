/** Network topology SVG component with ELK layout. */

import type { JSX } from "preact";
import { useEffect, useState } from "preact/hooks";
import { computeLayout, NODE_STYLES, type LayoutEdge, type LayoutResult } from "./layout";
import type { TopologyData } from "./types";

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
            <polygon points="0 0, 8 3, 0 6" fill="#666" />
          </marker>
        </defs>

        {/* Groups */}
        {layout.nodes
          .filter((n) => n.isGroup)
          .map((group) => {
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
                  fill={`${s?.color ?? "#bbb"}15`}
                  stroke={`${s?.color ?? "#bbb"}50`}
                  stroke-width="1.5"
                />
                {/* Group label */}
                <text x={group.x + 8} y={group.y + 15} font-size="11" font-weight="700" fill={s?.color ?? "#666"}>
                  {s?.icon ?? "?"} {group.id.replace("group:", "")}
                </text>

                {/* Sub-elements inside group */}
                {group.children.map((child) => (
                  <g
                    key={child.id}
                    onMouseEnter={(e: MouseEvent) =>
                      setTooltip({ x: e.clientX, y: e.clientY, title: child.id, lines: [`Type: ${child.type}`] })
                    }
                    onMouseLeave={hide}
                    style={{ cursor: "pointer" }}
                  >
                    <rect
                      x={group.x + child.x}
                      y={group.y + child.y}
                      width={child.width}
                      height={child.height}
                      rx={NODE_RX}
                      fill={s?.color ?? "#bbb"}
                      stroke="rgba(0,0,0,0.15)"
                      opacity="0.85"
                    />
                    <text
                      x={group.x + child.x + child.width / 2}
                      y={group.y + child.y + child.height / 2 + 4}
                      text-anchor="middle"
                      font-size="11"
                      font-weight="600"
                      fill="white"
                    >
                      {child.id}
                    </text>
                  </g>
                ))}

                {/* Ports with internal connections to child elements */}
                {group.ports.map((port) => {
                  const px = group.x + port.x + port.width / 2;
                  const py = group.y + port.y + port.height / 2;
                  // Find the nearest child element to draw a connection line
                  let nearestChild = group.children[0];
                  if (nearestChild !== undefined) {
                    let minDist = Infinity;
                    for (const child of group.children) {
                      const childCx = group.x + child.x + child.width / 2;
                      const childCy = group.y + child.y + child.height / 2;
                      const dist = Math.sqrt((px - childCx) ** 2 + (py - childCy) ** 2);
                      if (dist < minDist) {
                        minDist = dist;
                        nearestChild = child;
                      }
                    }
                    const childCx = group.x + nearestChild.x + (port.side === "WEST" ? 0 : nearestChild.width);
                    const childCy = group.y + nearestChild.y + nearestChild.height / 2;
                    return (
                      <g key={port.id}>
                        <line
                          x1={px}
                          y1={py}
                          x2={childCx}
                          y2={childCy}
                          stroke="#ccc"
                          stroke-width="1"
                          stroke-dasharray="3 2"
                        />
                        <circle cx={px} cy={py} r={3} fill="#888" />
                      </g>
                    );
                  }
                  return <circle key={port.id} cx={px} cy={py} r={3} fill="#888" />;
                })}
              </g>
            );
          })}

        {/* Edges with segment nodules */}
        {layout.edges.map((edge) => renderEdge(edge, setTooltip, hide))}
      </svg>

      {/* Tooltip overlay */}
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

function renderEdge(edge: LayoutEdge, setTooltip: (t: TooltipInfo) => void, hide: () => void): JSX.Element | null {
  if (edge.points.length < 2) return null;

  const d = edge.points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  return (
    <g key={`edge-${edge.name}`}>
      <path d={d} fill="none" stroke="#666" stroke-width="1.5" marker-end="url(#arrow)" />

      {/* Edge label */}
      {edge.points.length >= 2 && (
        <text
          x={(edge.points[0]!.x + edge.points[edge.points.length - 1]!.x) / 2}
          y={(edge.points[0]!.y + edge.points[edge.points.length - 1]!.y) / 2 - 8}
          text-anchor="middle"
          font-size="9"
          fill="#999"
        >
          {edge.name}
        </text>
      )}

      {/* Segment pill — connected series of segments */}
      {edge.segments.length > 0 &&
        (() => {
          const segs = edge.segments;
          // Center point of the segment cluster
          const cx = segs.reduce((sum, s) => sum + s.x, 0) / segs.length;
          const cy = segs.reduce((sum, s) => sum + s.y, 0) / segs.length;
          const cellW = 28;
          const cellH = 22;
          const totalW = segs.length * cellW;
          const startX = cx - totalW / 2;
          const startY = cy - cellH / 2;

          return (
            <g>
              {/* Background pill */}
              <rect
                x={startX}
                y={startY}
                width={totalW}
                height={cellH}
                rx={cellH / 2}
                fill="white"
                stroke="#999"
                stroke-width="1"
              />
              {/* Dividers and icons */}
              {segs.map((seg, i) => {
                const sx = startX + i * cellW + cellW / 2;
                const icon = SEGMENT_ICONS[seg.type] ?? "?";
                return (
                  <g
                    key={`${edge.name}-${seg.id}`}
                    onMouseEnter={(e: MouseEvent) =>
                      setTooltip({
                        x: e.clientX,
                        y: e.clientY,
                        title: seg.id,
                        lines: [`Type: ${seg.type.replace("Segment", "")}`, `Edge: ${edge.name}`],
                      })
                    }
                    onMouseLeave={hide}
                    style={{ cursor: "pointer" }}
                  >
                    {i > 0 && (
                      <line
                        x1={startX + i * cellW}
                        y1={startY + 3}
                        x2={startX + i * cellW}
                        y2={startY + cellH - 3}
                        stroke="#ddd"
                        stroke-width="1"
                      />
                    )}
                    <text x={sx} y={cy + 4} text-anchor="middle" font-size="12">
                      {icon}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })()}
    </g>
  );
}
