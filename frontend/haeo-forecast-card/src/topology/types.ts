/** Topology data types matching the Python serialize_topology() output. */

export interface TopologyNode {
  name: string;
  type: string; // "battery" | "grid" | "solar" | "inverter" | "load" | "node"
  group: string;
  /** VLAN IDs this node produces on (omitted if untagged). */
  outbound_tags?: number[];
  /** VLAN IDs this node accepts (omitted if untagged). */
  inbound_tags?: number[];
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
  /** VLAN IDs carried by this connection (omitted when only default tag 0). */
  tags?: number[];
}

export interface PolicyPricingTerm {
  connection: string;
  tag: number;
}

export interface PolicyPlacement {
  name: string;
  terms: PolicyPricingTerm[];
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  groups: Record<string, string[]>;
  /** Policy pricing placements (min-cut positions). */
  policies?: PolicyPlacement[];
}
