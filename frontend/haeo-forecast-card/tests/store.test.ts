import { describe, expect, it } from "vitest";

import { ForecastCardStore } from "../src/store";
import { loadScenarioHassState } from "./helpers/scenarioOutputs";

describe("ForecastCardStore", () => {
  it("builds filtered visible series from real scenario outputs", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario2"));
    store.setConfig({ type: "custom:haeo-forecast-card" });

    expect(store.hasData).toBe(true);
    expect(store.visibleSeries.length).toBeGreaterThan(1);
    expect(store.visibleSeries.some((series) => series.lane === "shadow")).toBe(false);
    expect(store.xDomain.max).toBeGreaterThan(store.xDomain.min);
  });

  it("computes hover rows and totals", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario3"));
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setSize(900, 380);
    store.setPointer(300, 120);

    expect(store.hoverTimeMs).not.toBeNull();
    expect(store.tooltipRows.length).toBeGreaterThan(0);
    expect(store.tooltipTotals.length).toBeGreaterThan(0);
  });

  it("supports reduced and smooth animation modes", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario4"));
    store.setConfig({
      type: "custom:haeo-forecast-card",
      animation_mode: "reduced",
      animation_speed: 1.5,
    });

    expect(store.motionMode).toBe("reduced");
    expect(store.animatedOffsetMs).toBe(0);

    store.setConfig({
      type: "custom:haeo-forecast-card",
      animation_mode: "smooth",
      animation_speed: 1.5,
    });
    store.setNow(store.xDomain.min + store.xDomain.step * 2);
    expect(store.animatedOffsetMs).toBeGreaterThanOrEqual(0);
  });

  it("toggles display mode and series visibility controls", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario4"));
    store.setConfig({ type: "custom:haeo-forecast-card", power_display_mode: "opposed" });
    store.setSize(1000, 420);

    expect(store.powerDisplayMode).toBe("opposed");
    store.togglePowerDisplayMode();
    expect(store.powerDisplayMode).toBe("overlay");

    const first = store.legendSeries[0];
    expect(first).toBeTruthy();
    if (!first) {
      return;
    }
    const before = store.visibleSeries.length;
    store.toggleSeriesVisibility(first.key);
    expect(store.visibleSeries.length).toBeLessThan(before);
    store.toggleSeriesVisibility(first.key);
    expect(store.visibleSeries.length).toBe(before);

    const firstElement = store.legendSeries[0]?.elementName ?? null;
    store.setHoveredLegendElement(firstElement);
    expect(store.focusedElementSeriesKeys.size).toBeGreaterThanOrEqual(0);
    store.setHoveredLegendElement(null);
    expect(store.focusedElementSeriesKeys.size).toBe(0);
  });
});
