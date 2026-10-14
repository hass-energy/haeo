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
  /** VLAN IDs carried by this connection (omitted when untagged / only tag 0). */
  tags?: number[];
}

export interface PolicyPricingTerm {
  connection: string;
  tag: number;
}

export interface PolicyPlacement {
  name: string;
  /** Human-readable label (e.g. "Battery → Load"). */
  label?: string;
  terms: PolicyPricingTerm[];
}

/** A reserve keeps energy for an outage; headroom keeps empty space for surplus. */
export type RequirementKind = "reserve" | "headroom";

export interface ReservePlacement {
  name: string;
  kind: RequirementKind;
  /** Loads and generation the reserve covers. */
  elements: string[];
  /** Batteries that hold the reserve together. */
  storage: string[];
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  groups: Record<string, string[]>;
  /** Policy pricing placements (min-cut positions). */
  policies?: PolicyPlacement[];
  /** Reserves and the elements they cover and are held by. */
  reserves?: ReservePlacement[];
}
