/**
 * Shared constants, lookups, and geometry helpers for topology rendering.
 *
 * Used by both the interactive Preact component (NetworkTopology.tsx) and
 * the headless SVG string renderer (render-svg.ts).
 */

import type { RequirementKind, ReservePlacement } from "./types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Point {
  x: number;
  y: number;
}

export interface ReserveRoles {
  /** Reserves and headroom this node holds. */
  holds: ReservePlacement[];
  /** Reserves and headroom this node's demand or generation counts toward. */
  covers: ReservePlacement[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Markers drawn on batteries that hold a reserve or headroom. */
export const REQUIREMENT_MARKERS: Record<RequirementKind, string> = { reserve: "🛡", headroom: "⤒" };

export const NODE_RX = 6;
export const GROUP_RX = 10;
export const PORT_EXTEND = 6;
export const ARROW_LEN = 10;
export const ARROW_HALF_W = 5;
export const STRIPE_GAP = 2.5;

/** Distinct colors for VLAN tags. Index 0 is unused (reserved). */
export const VLAN_COLORS: string[] = [
  "#888", // index 0 — reserved/fallback
  "#E91E63", // tag 1 — pink
  "#2196F3", // tag 2 — blue
  "#4CAF50", // tag 3 — green
  "#FF9800", // tag 4 — orange
  "#9C27B0", // tag 5 — purple
  "#00BCD4", // tag 6 — cyan
  "#CDDC39", // tag 7 — lime
];

export const SEGMENT_ICONS: Record<string, string> = {
  PricingSegment: "💲",
  PowerLimitSegment: "⚡",
  EfficiencySegment: "η",
  SocPricingSegment: "📊",
  TagFilterSegment: "🏷",
  TagPricingSegment: "🏷",
};

// ---------------------------------------------------------------------------
// Lookups
// ---------------------------------------------------------------------------

export function vlanColor(tag: number): string {
  return VLAN_COLORS[tag % VLAN_COLORS.length] ?? "#888";
}

// ---------------------------------------------------------------------------
// Geometry helpers
// ---------------------------------------------------------------------------

/**
 * Offset a polyline perpendicular to each segment direction.
 *
 * For each line segment, compute an independent perpendicular offset.
 * At corners where two segments meet, find the intersection of the two
 * offset lines (miter join) so parallel lines stay truly parallel through
 * orthogonal bends.
 */
export function offsetPoints(points: Point[], offset: number): Point[] {
  if (points.length < 2) return points.map((p) => ({ ...p }));

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

  const result: Point[] = [];
  for (let i = 0; i < points.length; i++) {
    const p = points[i]!;
    if (i === 0) {
      const n = normals[0]!;
      result.push({ x: p.x + n.nx * offset, y: p.y + n.ny * offset });
    } else if (i === points.length - 1) {
      const n = normals[normals.length - 1]!;
      result.push({ x: p.x + n.nx * offset, y: p.y + n.ny * offset });
    } else {
      const nA = normals[i - 1]!;
      const nB = normals[i]!;
      const dAx = points[i]!.x - points[i - 1]!.x;
      const dAy = points[i]!.y - points[i - 1]!.y;
      const dBx = points[i + 1]!.x - points[i]!.x;
      const dBy = points[i + 1]!.y - points[i]!.y;
      const cross = dAx * dBy - dAy * dBx;
      if (Math.abs(cross) < 1e-6) {
        result.push({ x: p.x + nA.nx * offset, y: p.y + nA.ny * offset });
        continue;
      }
      const oAx = p.x + nA.nx * offset;
      const oAy = p.y + nA.ny * offset;
      const oBx = p.x + nB.nx * offset;
      const oBy = p.y + nB.ny * offset;
      const t = ((oBx - oAx) * dBy - (oBy - oAy) * dBx) / cross;
      result.push({ x: oAx + t * dAx, y: oAy + t * dAy });
    }
  }
  return result;
}

/** Extend a polyline's first and last points outward along their segments. */
export function extendEndpoints(points: Point[], dist: number): Point[] {
  if (points.length < 2) return points;
  const result = points.map((p) => ({ ...p }));
  const dx0 = result[0]!.x - result[1]!.x;
  const dy0 = result[0]!.y - result[1]!.y;
  const len0 = Math.sqrt(dx0 * dx0 + dy0 * dy0);
  if (len0 > 0) {
    result[0] = { x: result[0]!.x + (dx0 / len0) * dist, y: result[0]!.y + (dy0 / len0) * dist };
  }
  const last = result.length - 1;
  const dx1 = result[last]!.x - result[last - 1]!.x;
  const dy1 = result[last]!.y - result[last - 1]!.y;
  const len1 = Math.sqrt(dx1 * dx1 + dy1 * dy1);
  if (len1 > 0) {
    result[last] = { x: result[last]!.x + (dx1 / len1) * dist, y: result[last]!.y + (dy1 / len1) * dist };
  }
  return result;
}

/** Escape text for safe SVG/HTML embedding. */
export function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/**
 * Compute arrow head geometry for an edge endpoint.
 * Returns the triangle vertices as {tip, left, right} or null if degenerate.
 */
export function computeArrowHead(
  points: Point[],
  reversed: boolean
): { tipX: number; tipY: number; left: Point; right: Point } | null {
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

  const tipX = tip.x + ux * (PORT_EXTEND / 2);
  const tipY = tip.y + uy * (PORT_EXTEND / 2);
  const baseX = tipX - ux * ARROW_LEN;
  const baseY = tipY - uy * ARROW_LEN;
  const left = { x: baseX + px * ARROW_HALF_W, y: baseY + py * ARROW_HALF_W };
  const right = { x: baseX - px * ARROW_HALF_W, y: baseY - py * ARROW_HALF_W };

  return { tipX, tipY, left, right };
}

/** Map each node to the reserves and headroom it holds or counts toward. */
export function reserveRoles(reserves: ReservePlacement[] | undefined): Map<string, ReserveRoles> {
  const roles = new Map<string, ReserveRoles>();
  const rolesFor = (name: string): ReserveRoles => {
    const existing = roles.get(name);
    if (existing !== undefined) return existing;
    const created: ReserveRoles = { holds: [], covers: [] };
    roles.set(name, created);
    return created;
  };
  for (const reserve of reserves ?? []) {
    for (const name of reserve.storage) rolesFor(name).holds.push(reserve);
    for (const name of reserve.elements) rolesFor(name).covers.push(reserve);
  }
  return roles;
}

/** Return the markers for the kinds of requirement a node holds, in a fixed order. */
export function reserveMarkers(roles: ReserveRoles | undefined): string {
  const kinds = new Set(roles?.holds.map((reserve) => reserve.kind));
  return (["reserve", "headroom"] as const)
    .filter((kind) => kinds.has(kind))
    .map((kind) => REQUIREMENT_MARKERS[kind])
    .join(" ");
}

/** Describe a node's reserve and headroom roles for its tooltip. */
export function reserveTooltipLines(roles: ReserveRoles | undefined): string[] {
  if (roles === undefined) return [];
  const lines: string[] = [];
  for (const kind of ["reserve", "headroom"] as const) {
    const held = roles.holds.filter((reserve) => reserve.kind === kind).map((reserve) => reserve.name);
    const covered = roles.covers.filter((reserve) => reserve.kind === kind).map((reserve) => reserve.name);
    if (held.length > 0) lines.push(`Holds ${kind}: ${held.join(", ")}`);
    if (covered.length > 0) lines.push(`Counted in ${kind}: ${covered.join(", ")}`);
  }
  return lines;
}
