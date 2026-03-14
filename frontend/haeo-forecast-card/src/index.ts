import "./card";
import "./editor";

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
