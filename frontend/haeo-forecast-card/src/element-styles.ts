/** The colour and icon that stand for each kind of HAEO element, wherever elements are drawn. */
export const NODE_STYLES: Record<string, { color: string; icon: string }> = {
  battery: { color: "#4CAF50", icon: "🔋" },
  deferrable_load: { color: "#8BC34A", icon: "⏱️" },
  ev: { color: "#00BCD4", icon: "🚗" },
  junction: { color: "#90CAF9", icon: "⚡" },
  node: { color: "#90CAF9", icon: "⚡" },
  grid: { color: "#FF9800", icon: "🏭" },
  solar: { color: "#FFD600", icon: "☀️" },
  load: { color: "#E91E63", icon: "🏠" },
  inverter: { color: "#9C27B0", icon: "🔄" },
  network: { color: "#607D8B", icon: "📡" },
  unknown: { color: "#BDBDBD", icon: "?" },
};
