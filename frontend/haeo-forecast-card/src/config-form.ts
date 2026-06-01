import { DEFAULT_HORIZON_PRESETS } from "./horizon-config";

interface ConfigFormSchema {
  name: string;
  required?: boolean;
  default?: boolean | string;
  selector: Record<string, unknown>;
}

interface ConfigFormDefinition {
  schema: ConfigFormSchema[];
  computeLabel: (schema: { name: string }) => string | undefined;
  computeHelper: (schema: { name: string }) => string | undefined;
}

const HORIZON_LABELS: Record<(typeof DEFAULT_HORIZON_PRESETS)[number], string> = {
  full: "Full forecast",
  "15m": "15 minutes",
  "30m": "30 minutes",
  "1h": "1 hour",
  "2h": "2 hours",
  "4h": "4 hours",
  "8h": "8 hours",
  "12h": "12 hours",
  "1d": "1 day",
  "2d": "2 days",
  "3d": "3 days",
};

export function buildHubConfigForm(): ConfigFormDefinition {
  return {
    schema: [
      { name: "title", selector: { text: {} } },
      {
        name: "hub_entry_id",
        required: true,
        selector: { config_entry: { integration: "haeo" } },
      },
      {
        name: "power_display_mode",
        default: "opposed",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { label: "Opposed", value: "opposed" },
              { label: "Overlay", value: "overlay" },
            ],
          },
        },
      },
      {
        name: "default_horizon",
        default: "full",
        selector: {
          select: {
            mode: "dropdown",
            options: DEFAULT_HORIZON_PRESETS.map((value) => ({
              label: HORIZON_LABELS[value],
              value,
            })),
          },
        },
      },
      {
        name: "tooltip_visible",
        default: true,
        selector: { boolean: {} },
      },
    ],
    computeLabel: (schema) => {
      if (schema.name === "title") {
        return "Title";
      }
      if (schema.name === "hub_entry_id") {
        return "HAEO hub";
      }
      if (schema.name === "power_display_mode") {
        return "Power display mode";
      }
      if (schema.name === "default_horizon") {
        return "Default horizon";
      }
      if (schema.name === "tooltip_visible") {
        return "Show information panel";
      }
      return undefined;
    },
    computeHelper: (schema) => {
      if (schema.name === "hub_entry_id") {
        return "Select the HAEO system this card should display.";
      }
      if (schema.name === "power_display_mode") {
        return "Choose whether positive and negative power draw on separate axes or overlap.";
      }
      if (schema.name === "default_horizon") {
        return "Initial time range for the horizon slider. Shorter values are used when the forecast is shorter.";
      }
      if (schema.name === "tooltip_visible") {
        return "Show the information panel with series values below the chart.";
      }
      return undefined;
    },
  };
}
