import "./card";
import "./editor.tsx";
import "./topology-card";
import "./topology-editor.tsx";

declare global {
  interface Window {
    customCards?: {
      type: string;
      name: string;
      description: string;
      documentationURL?: string;
      preview?: boolean;
    }[];
  }
}

window.customCards ??= [];
window.customCards.push({
  type: "haeo-forecast-card",
  name: "HAEO Forecast Card",
  description: "Interactive MobX + SVG stacked forecast chart for HAEO outputs.",
  documentationURL: "https://github.com/hass-energy/haeo/blob/main/docs/user-guide/lovelace-card.md",
  preview: true,
});
window.customCards.push({
  type: "haeo-topology-card",
  name: "HAEO Network Topology Card",
  description: "Interactive SVG graph of the HAEO optimization network.",
  documentationURL:
    "https://github.com/hass-energy/haeo/blob/main/docs/user-guide/lovelace-card.md#network-topology-card",
  preview: true,
});
