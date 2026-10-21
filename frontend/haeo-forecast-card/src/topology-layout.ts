/**
 * Lightweight topology layout sizing shared by the thin `haeo-topology-card`
 * element and its lazily-loaded rendering controller. Kept dependency-free so
 * the thin element can compute fallback sizes without importing the heavy
 * (ELK-bearing) controller module.
 */
export const TOPOLOGY_MASONRY_ROW_HEIGHT_PX = 50;
export const TOPOLOGY_DEFAULT_LAYOUT_HEIGHT_PX = 320;

export function topologyCardSize(layoutHeight: number): number {
  return Math.max(4, Math.ceil(layoutHeight / TOPOLOGY_MASONRY_ROW_HEIGHT_PX));
}
