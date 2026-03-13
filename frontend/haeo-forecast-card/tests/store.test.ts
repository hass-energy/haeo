import { describe, expect, it } from "vitest";

import { ForecastCardStore } from "../src/store";
import { loadScenarioHassState } from "./helpers/scenarioOutputs";

describe("ForecastCardStore", () => {
  it("builds lane groupings from real scenario outputs", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario2"));
    store.setConfig({ type: "custom:haeo-forecast-card" });

    expect(store.hasData).toBe(true);
    expect(store.laneSeries.size).toBeGreaterThan(1);
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
});
