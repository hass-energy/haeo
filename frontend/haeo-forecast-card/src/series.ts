import type { ForecastCardConfig, ForecastSeries, LaneType, SeriesSourceRole } from "./types";

type HassEntityState = {
  entity_id: string;
  state?: unknown;
  attributes: Record<string, unknown>;
};

type HassLike = {
  states: Record<string, HassEntityState | undefined>;
  language?: string;
  locale?: { language?: string };
};

export type { HassEntityState, HassLike };

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

function inferLane(outputType: string): LaneType {
  if (outputType === "power" || outputType === "power_limit") {
    return "power";
  }
  if (outputType === "price" || outputType === "cost") {
    return "price";
  }
  if (outputType === "state_of_charge") {
    return "soc";
  }
  if (outputType === "shadow_price") {
    return "shadow";
  }
  return "other";
}

function inferDrawType(outputType: string): "step" | "line" {
  return outputType === "state_of_charge" ? "line" : "step";
}

function fallbackLabel(elementName: string, outputName: string, outputType: string): string {
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
  if (outputType === "price") {
    const stem = normalizedOutput.replace(/\bprice\b/gi, "").trim();
    return stem ? `${elementName} ${stem} price`.trim() : `${elementName} price`;
  }
  return `${elementName} ${normalizedOutput}`.trim();
}

function hashString(value: string): number {
  let hash = 0;
  for (let idx = 0; idx < value.length; idx += 1) {
    hash = (hash * 31 + value.charCodeAt(idx)) >>> 0;
  }
  return hash;
}

function colorForElement(elementName: string, variant: number): string {
  const name = elementName.toLowerCase();
  if (name.includes("battery")) {
    const green = ["#22c55e", "#16a34a", "#15803d", "#4ade80"];
    return green[variant % green.length] ?? "#22c55e";
  }
  if (name.includes("grid")) {
    const blue = ["#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8", "#93c5fd"];
    return blue[variant % blue.length] ?? "#3b82f6";
  }
  if (name.includes("solar")) {
    const solar = ["#f59e0b", "#fbbf24", "#f97316", "#facc15", "#ea580c"];
    return solar[variant % solar.length] ?? "#f59e0b";
  }
  if (name.includes("load")) {
    const load = ["var(--haeo-load-0)", "var(--haeo-load-1)", "var(--haeo-load-2)", "var(--haeo-load-3)"];
    return load[variant % load.length] ?? "var(--haeo-load-0)";
  }
  const hue = hashString(elementName) % 360;
  const lightVariants = [46, 54, 38, 62];
  const lightness = lightVariants[variant % lightVariants.length] ?? 50;
  return `hsl(${hue} 72% ${lightness}%)`;
}

function includeOutputType(
  outputType: string,
  elementType: string,
  configMode: string | null,
  fieldName: string | null,
  direction: string | null
): boolean {
  if (outputType === "power") {
    // Plot power streams only when explicit directional metadata is present.
    // Aggregate "active power" streams do not have directional semantics.
    if (direction !== "+" && direction !== "-") {
      return false;
    }
  }
  if (outputType === "power" && configMode !== null) {
    // Input power entities should only appear when they are explicit forecasts.
    return fieldName === "forecast";
  }
  if (outputType === "power_limit") {
    // Keep parity with scenario plotting semantics: only solar power limits are visualized.
    return elementType === "solar";
  }
  return outputType === "power" || outputType === "price" || outputType === "state_of_charge";
}

function sourceRoleForSeries(configMode: string | null, fieldName: string | null): SeriesSourceRole {
  if (configMode === null) {
    return "output";
  }
  return fieldName === "forecast" ? "forecast" : "limit";
}

function fallbackPlotPriority(
  elementType: string,
  direction: string | null,
  outputType: string,
  sourceRole: SeriesSourceRole
): number | null {
  if (outputType !== "power" || sourceRole === "limit" || direction === null) {
    return null;
  }
  const key = `${elementType}:${direction}`;
  const byKey: Record<string, number> = {
    "load:-": 1,
    "solar:+": 2,
    "battery:-": 3,
    "battery:+": 4,
    "grid:+": 5,
    "grid:-": 6,
  };
  return byKey[key] ?? null;
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

    const points = rawForecast
      .map((item) => {
        if (!item || typeof item !== "object") {
          return null;
        }
        const row = item as Record<string, unknown>;
        const time = Date.parse(String(row["time"] ?? ""));
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

    const elementType = String(attrs["element_type"] ?? "");
    const configModeRaw = attrs["config_mode"];
    const configMode = typeof configModeRaw === "string" ? configModeRaw : null;
    const fieldNameRaw = attrs["field_name"];
    const fieldName = typeof fieldNameRaw === "string" ? fieldNameRaw : null;
    const sourceRoleRaw = attrs["source_role"];
    const sourceRole =
      sourceRoleRaw === "output" || sourceRoleRaw === "forecast" || sourceRoleRaw === "limit"
        ? sourceRoleRaw
        : sourceRoleForSeries(configMode, fieldName);
    const plotStreamRaw = attrs["plot_stream"];
    const plotStream = typeof plotStreamRaw === "string" ? plotStreamRaw : null;
    const plotPriorityRaw = attrs["plot_priority"];
    const plotPriorityFromMetadata = asNumber(plotPriorityRaw);
    const outputType = String(attrs["output_type"] ?? "other");
    const elementName = String(attrs["element_name"] ?? entityId);
    const outputName = String(attrs["output_name"] ?? outputType);
    const directionRaw = attrs["direction"];
    const direction = directionRaw === "+" || directionRaw === "-" ? directionRaw : null;
    if (!includeOutputType(outputType, elementType, configMode, fieldName, direction)) {
      continue;
    }
    const plotPriority =
      plotPriorityFromMetadata ?? fallbackPlotPriority(elementType, direction, outputType, sourceRole);
    const unit = String(attrs["unit_of_measurement"] ?? "");
    const friendlyName = String(attrs["friendly_name"] ?? "");
    const variant = elementVariantCount.get(elementName) ?? 0;
    elementVariantCount.set(elementName, variant + 1);

    result.push({
      key: `${entityId}:${outputName}`,
      entityId,
      label: friendlyName || fallbackLabel(elementName, outputName, outputType),
      elementName,
      elementType,
      outputName,
      outputType,
      direction,
      configMode,
      fieldName,
      sourceRole,
      plotStream,
      plotPriority,
      lane: inferLane(outputType),
      drawType: inferDrawType(outputType),
      unit,
      color: colorForElement(elementName, variant),
      times,
      values,
      points: sortedPoints,
    });
  }

  return result.sort((a, b) => a.label.localeCompare(b.label));
}
