/** Network topology SVG component. */

import type { JSX } from "preact";
import { useMemo, useState } from "preact/hooks";
import { computeLayout, NODE_STYLES, type LayoutResult, type LayoutSegmentNodule } from "./layout";
import type { TopologyData } from "./types";

const NODULE_RADIUS = 8;
const NODE_CORNER_RADIUS = 8;
const GROUP_CORNER_RADIUS = 12;
const SEGMENT_LABELS: Record<string, string> = {
  PricingSegment: "💲",
  PowerLimitSegment: "⚡",
  EfficiencySegment: "η",
  SocPricingSegment: "📊",
  TagFilterSegment: "🏷",
  TagPricingSegment: "🏷",
  PassthroughSegment: "",
};

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
  const { topology, width: propWidth, height: propHeight } = props;
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  const layout: LayoutResult = useMemo(() => computeLayout(topology), [topology]);
  const width = propWidth ?? layout.width;
  const height = propHeight ?? layout.height;

  const handleNodeHover = (e: MouseEvent, name: string, type: string, group: string): void => {
    setTooltip({
      x: e.clientX,
      y: e.clientY,
      title: name,
      details: [
        { label: "Type", value: type },
        { label: "Group", value: group },
      ],
    });
  };

  const handleSegmentHover = (e: MouseEvent, seg: LayoutSegmentNodule): void => {
    setTooltip({
      x: e.clientX,
      y: e.clientY,
      title: `${seg.edgeName} → ${seg.id}`,
      details: [{ label: "Segment", value: seg.type.replace("Segment", "") }],
    });
  };

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
        {/* Groups (background containers) */}
        {layout.groups.map((group) => (
          <g key={`group-${group.name}`}>
            <rect
              x={group.x}
              y={group.y}
              width={group.width}
              height={group.height}
              rx={GROUP_CORNER_RADIUS}
              fill="rgba(200,200,200,0.15)"
              stroke="rgba(150,150,150,0.4)"
              stroke-width="1"
              stroke-dasharray="4 2"
            />
            <text x={group.x + 8} y={group.y + 14} font-size="11" fill="rgba(100,100,100,0.8)" font-weight="600">
              {group.name}
            </text>
          </g>
        ))}

        {/* Edges */}
        {layout.edges.map((edge) => {
          const d = edge.points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
          return (
            <g key={`edge-${edge.name}`}>
              <path d={d} fill="none" stroke="#666" stroke-width="1.5" marker-end="url(#arrowhead)" />
              {/* Segment nodules along the edge */}
              {edge.segments.map((seg) => {
                const label = SEGMENT_LABELS[seg.type] ?? "?";
                if (!label) return null;
                return (
                  <g
                    key={`seg-${edge.name}-${seg.id}`}
                    onMouseEnter={(e: MouseEvent) => handleSegmentHover(e, seg)}
                    onMouseLeave={handleMouseLeave}
                    style={{ cursor: "pointer" }}
                  >
                    <circle cx={seg.x} cy={seg.y} r={NODULE_RADIUS} fill="white" stroke="#999" stroke-width="1" />
                    <text x={seg.x} y={seg.y + 4} text-anchor="middle" font-size="10">
                      {label}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* Nodes */}
        {layout.nodes.map((node) => {
          const style = NODE_STYLES[node.type] ?? NODE_STYLES["unknown"];
          return (
            <g
              key={`node-${node.id}`}
              onMouseEnter={(e: MouseEvent) => handleNodeHover(e, node.id, node.type, node.group)}
              onMouseLeave={handleMouseLeave}
              style={{ cursor: "pointer" }}
            >
              <rect
                x={node.x - node.width / 2}
                y={node.y - node.height / 2}
                width={node.width}
                height={node.height}
                rx={NODE_CORNER_RADIUS}
                fill={style?.color ?? "#BDBDBD"}
                stroke="rgba(0,0,0,0.2)"
                stroke-width="1"
                opacity="0.85"
              />
              <text x={node.x} y={node.y - 4} text-anchor="middle" font-size="12" font-weight="600" fill="white">
                {style?.icon ?? "?"} {node.id}
              </text>
              <text x={node.x} y={node.y + 12} text-anchor="middle" font-size="9" fill="rgba(255,255,255,0.7)">
                {node.type}
              </text>
            </g>
          );
        })}

        {/* Arrow marker definition */}
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#666" />
          </marker>
        </defs>
      </svg>

      {/* Tooltip overlay */}
      {tooltip && (
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
