/** Network topology SVG component using ELK layout. */

import type { JSX } from "preact";
import { useEffect, useState } from "preact/hooks";
import { computeLayout, NODE_STYLES, type LayoutEdge, type LayoutResult } from "./layout";
import type { TopologyData } from "./types";

const NODE_CORNER_RADIUS = 8;
const GROUP_CORNER_RADIUS = 12;

interface TooltipInfo {
  x: number;
  y: number;
  title: string;
  details: Array<{ label: string; value: string }>;
}

interface NetworkTopologyProps {
  topology: TopologyData;
  width?: number;
  height?: number;
}

export function NetworkTopology(props: NetworkTopologyProps): JSX.Element {
  const { topology } = props;
  const [layout, setLayout] = useState<LayoutResult | null>(null);
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  useEffect(() => {
    void computeLayout(topology).then(setLayout);
  }, [topology]);

  if (layout == null) {
    return <div>Computing layout…</div>;
  }

  const width = props.width ?? layout.width;
  const height = props.height ?? layout.height;

  const handleMouseLeave = (): void => setTooltip(null);

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        class="topologyGraph"
      >
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#666" />
          </marker>
        </defs>

        {/* Group containers */}
        {layout.nodes
          .filter((n) => n.isGroup)
          .map((group) => {
            const style = NODE_STYLES[group.type] ?? NODE_STYLES["unknown"];
            return (
              <g key={group.id}>
                <rect
                  x={group.x}
                  y={group.y}
                  width={group.width}
                  height={group.height}
                  rx={GROUP_CORNER_RADIUS}
                  fill={`${style?.color ?? "#BDBDBD"}18`}
                  stroke={`${style?.color ?? "#BDBDBD"}60`}
                  stroke-width="1.5"
                />
                <text x={group.x + 10} y={group.y + 16} font-size="12" font-weight="700" fill={style?.color ?? "#666"}>
                  {style?.icon ?? "?"} {group.id.replace("group:", "")}
                </text>

                {/* Child nodes inside group */}
                {group.children.map((child) => {
                  const isSegment = child.type === "segment";
                  return (
                    <g
                      key={child.id}
                      onMouseEnter={(e: MouseEvent) => {
                        setTooltip({
                          x: e.clientX,
                          y: e.clientY,
                          title: child.id.startsWith("seg:") ? child.id.split(":").slice(1).join(":") : child.id,
                          details: [{ label: "Type", value: child.type }],
                        });
                      }}
                      onMouseLeave={handleMouseLeave}
                      style={{ cursor: "pointer" }}
                    >
                      <rect
                        x={group.x + child.x}
                        y={group.y + child.y}
                        width={child.width}
                        height={child.height}
                        rx={isSegment ? 4 : NODE_CORNER_RADIUS}
                        fill={isSegment ? "#FFF" : (style?.color ?? "#BDBDBD")}
                        stroke={isSegment ? "#999" : "rgba(0,0,0,0.15)"}
                        stroke-width="1"
                        opacity={isSegment ? 1 : 0.85}
                      />
                      <text
                        x={group.x + child.x + child.width / 2}
                        y={group.y + child.y + child.height / 2 + 4}
                        text-anchor="middle"
                        font-size={isSegment ? "10" : "11"}
                        font-weight={isSegment ? "400" : "600"}
                        fill={isSegment ? "#333" : "white"}
                      >
                        {child.id.startsWith("seg:") ? child.id.split(":").pop() : child.id}
                      </text>
                    </g>
                  );
                })}

                {/* Ports */}
                {group.ports.map((port) => (
                  <circle
                    key={port.id}
                    cx={group.x + port.x + port.width / 2}
                    cy={group.y + port.y + port.height / 2}
                    r={4}
                    fill="#666"
                  />
                ))}
              </g>
            );
          })}

        {/* Edges */}
        {layout.edges.map((edge) => renderEdge(edge))}
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
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: "4px" }}>{tooltip.title}</div>
          {tooltip.details.map((d) => (
            <div key={d.label} style={{ opacity: 0.8 }}>
              {d.label}: {d.value}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function renderEdge(edge: LayoutEdge): JSX.Element | null {
  if (edge.sections.length === 0) return null;

  const pathParts: string[] = [];
  for (const section of edge.sections) {
    pathParts.push(`M ${section.startPoint.x} ${section.startPoint.y}`);
    for (const bp of section.bendPoints ?? []) {
      pathParts.push(`L ${bp.x} ${bp.y}`);
    }
    pathParts.push(`L ${section.endPoint.x} ${section.endPoint.y}`);
  }

  return (
    <g key={`edge-${edge.name}`}>
      <path d={pathParts.join(" ")} fill="none" stroke="#666" stroke-width="1.5" marker-end="url(#arrowhead)" />
      <text
        x={(edge.sections[0]!.startPoint.x + edge.sections[0]!.endPoint.x) / 2}
        y={(edge.sections[0]!.startPoint.y + edge.sections[0]!.endPoint.y) / 2 - 6}
        text-anchor="middle"
        font-size="9"
        fill="#888"
      >
        {edge.name}
      </text>
    </g>
  );
}
