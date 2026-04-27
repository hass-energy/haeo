/** Topology data types matching the Python serialize_topology() output. */

export interface TopologyNode {
  name: string;
  type: string; // "battery" | "node" | "unknown"
  group: string;
}

export interface TopologySegment {
  id: string;
  type: string; // "PricingSegment" | "PowerLimitSegment" | "EfficiencySegment" etc.
}

export interface TopologyEdge {
  name: string;
  source: string;
  target: string;
  segments: TopologySegment[];
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  groups: Record<string, string[]>;
}
