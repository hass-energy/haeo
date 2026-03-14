import type { ForecastCardConfig, ForecastSeries, LaneType } from "./types";

const COLORS = [
  "#4f46e5",
  "#059669",
  "#d97706",
  "#db2777",
  "#0ea5e9",
  "#7c3aed",
  "#16a34a",
  "#f43f5e",
  "#ea580c",
  "#0284c7",
];

type HassEntityState = {
  entity_id: string;
  attributes: Record<string, unknown>;
};

type HassLike = {
  states: Record<string, HassEntityState | undefined>;
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
  if (outputType === "power" || outputType === "power_flow" || outputType === "power_limit") {
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
  let colorIndex = 0;

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

    const outputType = String(attrs["output_type"] ?? "other");
    const elementName = String(attrs["element_name"] ?? entityId);
    const outputName = String(attrs["output_name"] ?? outputType);
    const unit = String(attrs["unit_of_measurement"] ?? "");
    const friendlyName = String(attrs["friendly_name"] ?? "");

    result.push({
      key: `${entityId}:${outputName}`,
      entityId,
      label: friendlyName || fallbackLabel(elementName, outputName, outputType),
      elementName,
      outputName,
      outputType,
      lane: inferLane(outputType),
      drawType: inferDrawType(outputType),
      unit,
      color: COLORS[colorIndex % COLORS.length] ?? "#4f46e5",
      times,
      values,
      points: sortedPoints,
    });
    colorIndex += 1;
  }

  return result.sort((a, b) => a.label.localeCompare(b.label));
}
