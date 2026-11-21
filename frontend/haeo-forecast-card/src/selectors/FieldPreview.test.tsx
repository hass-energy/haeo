import { render } from "preact";
import { act as actAsync } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { FieldPreview, previewGeometry } from "./FieldPreview";
import type { PreviewResult } from "./FieldPreview";
import type { SelectorHass } from "./types";

const HOUR = 3600;
const START = Date.UTC(2026, 0, 1, 0, 0) / 1000;
const RESULT: PreviewResult = {
  times: [START, START + HOUR, START + 2 * HOUR, START + 3 * HOUR],
  values: [0.5, 1, 3],
  days: [START + 2 * HOUR],
};

const t = (key: string, values: Record<string, string> = {}): string =>
  key === "input.options.preview"
    ? `Combined: now ${values["now"] ?? ""}, then ${values["min"] ?? ""} to ${values["max"] ?? ""} over the next ${values["hours"] ?? ""} hours`
    : key;

describe("previewGeometry", () => {
  it("plots what follows now as steps across each interval, scaled from zero to the highest value", () => {
    const geometry = previewGeometry(RESULT, false);
    expect(geometry.line).toBe("0.0,31.0 150.0,31.0 150.0,3.0 300.0,3.0");
    expect([geometry.min, geometry.max, geometry.hours]).toEqual([0, 3, 2]);
    expect(geometry.midnights).toEqual([150]);
    expect(geometry.zero).toBeNull();
  });

  it("draws a zero line when values go below zero", () => {
    const geometry = previewGeometry({ ...RESULT, values: [0, -1, 1] }, false);
    expect(geometry.zero).toBeCloseTo(24);
  });
});

let container: HTMLElement;

beforeEach(() => {
  vi.useFakeTimers();
  container = document.createElement("div");
  document.body.append(container);
});

afterEach(() => {
  render(null, container);
  container.remove();
  vi.useRealTimers();
});

async function show(callWS: SelectorHass["callWS"]): Promise<void> {
  const hass: SelectorHass = { states: {}, localize: () => "", language: "en", ...(callWS ? { callWS } : {}) };
  await actAsync(() => {
    render(
      <FieldPreview
        hass={hass}
        preview={{ entry_id: "hub", output_type: "power", boundaries: false, non_negative: true }}
        entityIds={["sensor.forecast", "sensor.house"]}
        unit="kW"
        t={t}
      />,
      container
    );
  });
  await actAsync(async () => {
    await vi.advanceTimersByTimeAsync(200);
  });
}

describe("FieldPreview", () => {
  it("asks the integration to combine the field's entities, and shows now beside the combined forecast", async () => {
    const callWS = vi.fn().mockResolvedValue(RESULT);
    await show(callWS as SelectorHass["callWS"]);

    expect(callWS).toHaveBeenCalledWith({
      type: "haeo/input_preview",
      entry_id: "hub",
      output_type: "power",
      boundaries: false,
      non_negative: true,
      entity_ids: ["sensor.forecast", "sensor.house"],
    });
    const plot = container.querySelector(".preview-plot");
    expect(plot?.getAttribute("aria-label")).toBe("Combined: now 0.5 kW, then 0 kW to 3 kW over the next 2 hours");
    expect(plot?.querySelector(".readout-value")?.textContent).toBe("0.5");
    expect(plot?.querySelector(".plot-max")?.textContent).toBe("3 kW");
  });

  it("shows nothing when the integration cannot combine the entities", async () => {
    const callWS = vi.fn().mockRejectedValue(new Error("not_found"));
    await show(callWS as SelectorHass["callWS"]);
    expect(container.querySelector(".preview-plot")).toBeNull();
  });

  it("shows nothing without a websocket connection", async () => {
    await show(undefined);
    expect(container.querySelector(".preview-plot")).toBeNull();
  });
});
