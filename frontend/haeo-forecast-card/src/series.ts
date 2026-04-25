import type {
  ForecastCardConfig,
  ForecastSeries,
  CardOutputType,
  ElementType,
  LaneType,
  SeriesSourceRole,
} from "./types";
import type { ConfigMode } from "./types";

interface HassEntityState {
  entity_id: string;
  state?: unknown;
  attributes: Record<string, unknown>;
}

interface HassLike {
  states: Record<string, HassEntityState | undefined>;
  language?: string;
  locale?: { language?: string };
}

export type { HassEntityState, HassLike };

function asString(value: unknown, fallback = ""): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function inferLane(outputType: CardOutputType): LaneType {
  if (outputType === "power") {
    return "power";
  }
  if (outputType === "price") {
    return "price";
  }
  return "soc";
}

function inferDrawType(outputType: CardOutputType): "step" | "line" {
  return outputType === "state_of_charge" ? "line" : "step";
}

function fallbackLabel(elementName: string, outputName: string, outputType: CardOutputType): string {
  const normalizedOutput = outputName.replace(/_/g, " ").trim();
  if (outputType === "state_of_charge") {
    return `${elementName} state of charge`.trim();
  }
  if (outputType === "power") {
    const stem = normalizedOutput.replace(/\bpower\b/gi, "").trim();
    if (!stem) {
      return elementName;
    }
    const el = elementName.toLowerCase();
    const st = stem.toLowerCase();
    if (el.includes(st) || st.includes(el)) {
      return elementName;
    }
    return `${elementName} ${stem}`.trim();
  }
  const stem = normalizedOutput.replace(/\bprice\b/gi, "").trim();
  return stem ? `${elementName} ${stem} price`.trim() : `${elementName} price`;
}

function hashString(value: string): number {
  let hash = 0;
  for (let idx = 0; idx < value.length; idx += 1) {
    hash = (hash * 31 + value.charCodeAt(idx)) >>> 0;
  }
  return hash;
}

function colorForElement(elementType: ElementType, elementName: string, variant: number): string {
  if (elementType === "battery") {
    const green = ["#22c55e", "#16a34a", "#15803d", "#4ade80"];
    return green[variant % green.length] ?? "#22c55e";
  }
  if (elementType === "grid") {
    const blue = ["#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8", "#93c5fd"];
    return blue[variant % blue.length] ?? "#3b82f6";
  }
  if (elementType === "solar") {
    const solar = ["#f59e0b", "#fbbf24", "#f97316", "#facc15", "#ea580c"];
    return solar[variant % solar.length] ?? "#f59e0b";
  }
  if (elementType === "load") {
    const load = ["var(--haeo-load-0)", "var(--haeo-load-1)", "var(--haeo-load-2)", "var(--haeo-load-3)"];
    return load[variant % load.length] ?? "var(--haeo-load-0)";
  }
  const hue = hashString(elementName) % 360;
  const lightVariants = [46, 54, 38, 62];
  const lightness = lightVariants[variant % lightVariants.length] ?? 50;
  return `hsl(${hue} 72% ${lightness}%)`;
}

const ELEMENT_TYPES: ReadonlySet<string> = new Set<ElementType>([
  "battery",
  "battery_section",
  "connection",
  "grid",
  "inverter",
  "load",
  "node",
  "solar",
  "policy",
]);

function isElementType(value: string): value is ElementType {
  return ELEMENT_TYPES.has(value);
}

function includeOutputType(outputType: string, direction: "+" | "-" | null): outputType is CardOutputType {
  if (outputType === "power") {
    // Plot power streams only when explicit directional metadata is present.
    if (direction !== "+" && direction !== "-") {
      return false;
    }
  }
  return outputType === "power" || outputType === "price" || outputType === "state_of_charge";
}

function sourceRoleForSeries(configMode: string | null, fieldName: string | null): SeriesSourceRole {
  if (configMode === null) {
    return "output";
  }
  return fieldName === "forecast" ? "forecast" : "limit";
}

export function normalizeSeries(hass: HassLike | null, config: ForecastCardConfig): ForecastSeries[] {
  if (!hass) {
    return [];
  }
  const configured = config.entities ?? [];
  const entityIds =
    configured.length > 0
      ? configured
      : Object.keys(hass.states).filter((entityId) => {
          const state = hass.states[entityId];
          return Boolean(state?.attributes["forecast"]);
        });

  const result: ForecastSeries[] = [];
  const elementVariantCount = new Map<string, number>();

  for (const entityId of entityIds) {
    const state = hass.states[entityId];
    if (!state) {
      continue;
    }
    const attrs = state.attributes;
    const rawForecast = attrs["forecast"];
    if (!Array.isArray(rawForecast) || rawForecast.length < 2) {
      continue;
    }

    const points = (rawForecast as unknown[])
      .map((item) => {
        if (item === null || item === undefined || typeof item !== "object") {
          return null;
        }
        const row = item as Record<string, unknown>;
        const timeRaw = row["time"];
        const time = Date.parse(asString(timeRaw));
        const value = asNumber(row["value"]);
        if (!Number.isFinite(time) || value === null) {
          return null;
        }
        return { time, value };
      })
      .filter((point): point is { time: number; value: number } => point !== null);

    if (points.length < 2) {
      continue;
    }
    const sortedPoints = points.sort((a, b) => a.time - b.time);
    const times = new Float64Array(sortedPoints.length);
    const values = new Float64Array(sortedPoints.length);
    for (let idx = 0; idx < sortedPoints.length; idx += 1) {
      const point = sortedPoints[idx];
      if (!point) {
        continue;
      }
      times[idx] = point.time;
      values[idx] = point.value;
    }

    const elementTypeRaw = asString(attrs["element_type"]);
    if (!isElementType(elementTypeRaw)) {
      continue;
    }
    const elementType = elementTypeRaw;
    const configModeRaw = asString(attrs["config_mode"]);
    const configMode: ConfigMode | null =
      configModeRaw === "editable" || configModeRaw === "driven" ? configModeRaw : null;
    const fixed = attrs["fixed"] === true;
    const fieldNameRaw = attrs["field_name"];
    const fieldName = typeof fieldNameRaw === "string" ? fieldNameRaw : null;
    const sourceRoleRaw = attrs["source_role"];
    const sourceRole =
      sourceRoleRaw === "output" || sourceRoleRaw === "forecast" || sourceRoleRaw === "limit"
        ? sourceRoleRaw
        : sourceRoleForSeries(configMode, fieldName);
    const priorityRaw = attrs["priority"];
    const priority = asNumber(priorityRaw);
    const outputType = asString(attrs["field_type"], "other");
    const elementName = asString(attrs["element_name"], entityId);
    const outputName = asString(attrs["output_name"], outputType);
    const directionRaw = attrs["direction"];
    const direction = directionRaw === "+" || directionRaw === "-" ? directionRaw : null;
    if (!includeOutputType(outputType, direction)) {
      continue;
    }
    const unit = asString(attrs["unit_of_measurement"]);
    const friendlyName = asString(attrs["friendly_name"]);
    const variant = elementVariantCount.get(elementName) ?? 0;
    elementVariantCount.set(elementName, variant + 1);

    result.push({
      key: `${entityId}:${outputName}`,
      entityId,
      label: friendlyName !== "" ? friendlyName : fallbackLabel(elementName, outputName, outputType),
      elementName,
      elementType,
      outputName,
      outputType,
      configMode,
      fixed,
      direction,
      sourceRole,
      priority,
      lane: inferLane(outputType),
      drawType: inferDrawType(outputType),
      unit,
      color: colorForElement(elementType, elementName, variant),
      times,
      values,
    });
  }

  return result.sort((a, b) => a.label.localeCompare(b.label));
}
