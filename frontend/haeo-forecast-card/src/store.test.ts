import { describe, expect, it, vi } from "vitest";

import { ForecastCardStore } from "./store";
import { loadScenarioHassState } from "./fixtures/scenarioOutputs";
import type { HassLike } from "./series";

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

  it("computes hover rows", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario3"));
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setSize(900, 380);
    store.setPointer(300, 120);

    expect(store.hoverTimeMs).not.toBeNull();
    expect(store.tooltipRows.length).toBeGreaterThan(0);
  });

  it("keeps limit series available for tooltip values without plotting them", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario1"));
    store.setConfig({ type: "custom:haeo-forecast-card" });

    expect(store.visibleSeries.some((series) => series.sourceRole === "limit" && series.lane === "power")).toBe(true);
    expect(store.powerSeries.some((series) => series.sourceRole === "limit")).toBe(false);
  });

  it("shows grid limits as paired tooltip totals even when default-hidden", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario1"));
    store.setConfig({ type: "custom:haeo-forecast-card" });

    const gridLimitKeys = store.normalizedSeries
      .filter((series) => series.elementName === "Grid" && series.sourceRole === "limit" && series.lane === "power")
      .map((series) => series.key);

    expect(gridLimitKeys.length).toBeGreaterThan(0);
    expect(gridLimitKeys.every((key) => store.hiddenSeriesKeys.has(key))).toBe(true);
    expect(
      store.tooltipRows.some(
        (row) => row.key.includes("grid_power_import") && gridLimitKeys.includes(row.possibleKey ?? "")
      )
    ).toBe(true);
    expect(
      store.tooltipRows.some(
        (row) => row.key.includes("grid_power_export") && gridLimitKeys.includes(row.possibleKey ?? "")
      )
    ).toBe(true);
  });

  it("allocates extra height for narrow wrapped layouts", () => {
    const store = new ForecastCardStore();

    expect(store.responsiveHeight(360)).toBe(680);
    expect(store.responsiveHeight(360)).toBeGreaterThan(store.responsiveHeight(641));
    store.setSize(360, 300, 520);
    expect(store.cardWidth).toBe(520);
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
    expect(store.tooltipVisible).toBe(true);
    store.toggleTooltipVisibility();
    expect(store.tooltipVisible).toBe(false);

    const first = store.visibleSeries[0] ?? store.legendSeries[0];
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

  it("uses step interval index before midpoint switch", () => {
    const store = new ForecastCardStore();
    const hass: HassLike = {
      states: {
        "sensor.test_power": {
          entity_id: "sensor.test_power",
          attributes: {
            field_type: "power",
            output_name: "load_power",
            direction: "-",
            element_type: "load",
            element_name: "Load",
            unit_of_measurement: "kW",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1 },
              { time: "2026-03-14T00:10:00Z", value: 2 },
              { time: "2026-03-14T00:20:00Z", value: 3 },
            ],
          },
        },
      },
    };
    store.setHass(hass);
    store.setConfig({ type: "custom:haeo-forecast-card", animation_mode: "off" });
    store.setSize(900, 380);

    const series = store.visibleSeries[0];
    expect(series).toBeTruthy();
    if (!series) {
      return;
    }
    const first = series.times[0] ?? 0;
    const second = series.times[1] ?? first;
    const midpoint = first + (second - first) * 0.5;
    store.setPointer(store.xScale(midpoint), 120);

    expect(store.hoverIndices.get(series.key)).toBe(0);
  });

  it("clips xDomain when horizon is set", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario2"));
    store.setConfig({ type: "custom:haeo-forecast-card" });

    const fourHoursMs = 4 * 3_600_000;
    const fullMax = store.xDomain.max;
    expect(store.horizonOptions).toContain(fourHoursMs);
    expect(store.horizonOptions[store.horizonOptions.length - 1]).toBeNull();
    expect(store.horizonRevision).toBe(0);
    store.setHorizon(fourHoursMs);
    expect(store.horizonRevision).toBe(1);
    expect(store.horizonDurationMs).toBe(fourHoursMs);
    expect(store.horizonAnimation).not.toBeNull();
    expect(store.selectedXDomain.max).toBeLessThanOrEqual(store.selectedXDomain.min + fourHoursMs);
    expect(store.selectedXDomain.max).toBeLessThan(fullMax);
    store.setHorizon(fourHoursMs);
    expect(store.horizonRevision).toBe(1);

    store.setHorizon(null);
    expect(store.horizonRevision).toBe(2);
    expect(store.xDomain.max).toBe(fullMax);
  });

  it("finishes horizon animations and clears stale hover state", () => {
    let frameCallback: FrameRequestCallback = () => undefined;
    let frameCallbackSet = false;
    const requestFrame = vi.spyOn(globalThis, "requestAnimationFrame").mockImplementation((callback) => {
      frameCallback = callback;
      frameCallbackSet = true;
      return 1;
    });
    const cancelFrame = vi.spyOn(globalThis, "cancelAnimationFrame").mockImplementation(() => undefined);
    try {
      const store = new ForecastCardStore();
      store.setHass(loadScenarioHassState("scenario2"));
      store.setConfig({ type: "custom:haeo-forecast-card" });
      store.setHoveredLegendElement("missing element");
      store.setHighlightedSeries("missing:series");

      store.setHorizon(4 * 3_600_000);
      expect(store.horizonAnimation).not.toBeNull();
      expect(frameCallbackSet).toBe(true);
      frameCallback(store.horizonAnimationNowMs + 250);
      expect(store.horizonAnimation).toBeNull();
      expect(cancelFrame).not.toHaveBeenCalled();

      store.setHass({ states: {} });
      expect(store.hoveredLegendElement).toBeNull();
      expect(store.highlightedSeries).toBeNull();
    } finally {
      requestFrame.mockRestore();
      cancelFrame.mockRestore();
    }
  });

  it("hides policy series by default", () => {
    const store = new ForecastCardStore();
    store.setHass({
      states: {
        "sensor.policy_power": {
          entity_id: "sensor.policy_power",
          attributes: {
            field_type: "power",
            output_name: "active_power",
            direction: "+",
            element_type: "policy",
            element_name: "Policy",
            unit_of_measurement: "kW",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1 },
              { time: "2026-03-14T00:10:00Z", value: 1 },
            ],
          },
        },
      },
    });
    store.setConfig({ type: "custom:haeo-forecast-card" });

    expect(store.hiddenSeriesKeys.size).toBe(1);
    expect(store.visibilityRevision).toBe(1);
  });

  it("keeps potential totals for fixed elements", () => {
    const store = new ForecastCardStore();
    const hass: HassLike = {
      states: {
        "sensor.load_power": {
          entity_id: "sensor.load_power",
          attributes: {
            field_type: "power",
            output_name: "load_power",
            direction: "-",
            element_type: "load",
            element_name: "Constant Load",
            unit_of_measurement: "kW",
            source_role: "output",
            fixed: true,
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1 },
              { time: "2026-03-14T00:10:00Z", value: 1 },
            ],
          },
        },
        "sensor.load_forecast": {
          entity_id: "sensor.load_forecast",
          attributes: {
            field_type: "power",
            output_name: "load_forecast",
            direction: "-",
            element_type: "load",
            element_name: "Constant Load",
            unit_of_measurement: "kW",
            source_role: "forecast",
            config_mode: "driven",
            field_name: "forecast",
            forecast: [
              { time: "2026-03-14T00:00:00Z", value: 1 },
              { time: "2026-03-14T00:10:00Z", value: 1 },
            ],
          },
        },
      },
    };
    store.setHass(hass);
    store.setConfig({ type: "custom:haeo-forecast-card" });

    expect(store.normalizedSeries.some((s) => s.sourceRole === "output")).toBe(true);
    expect(store.normalizedSeries.some((s) => s.sourceRole === "forecast")).toBe(true);
    expect(store.tooltipRows[0]).toMatchObject({
      key: "sensor.load_power:load_power",
      possibleKey: "sensor.load_forecast:load_forecast",
      value: -1,
      possibleValue: -1,
    });
  });

  it("toggles element visibility for all series of an element", () => {
    const store = new ForecastCardStore();
    store.setHass(loadScenarioHassState("scenario2"));
    store.setConfig({ type: "custom:haeo-forecast-card" });

    const firstElement = store.legendSeries[0]?.elementName ?? null;
    expect(firstElement).not.toBeNull();
    if (firstElement === null) return;

    const elementSeries = store.legendSeries.filter((s) => s.elementName === firstElement);
    const allVisibleBefore = elementSeries.every((s) => store.visibleSeries.some((v) => v.key === s.key));

    store.toggleElementVisibility(firstElement);

    if (allVisibleBefore) {
      // All series for the element should now be hidden
      expect(elementSeries.every((s) => !store.visibleSeries.some((v) => v.key === s.key))).toBe(true);
    }

    // Toggle back
    store.toggleElementVisibility(firstElement);
    expect(elementSeries.every((s) => store.visibleSeries.some((v) => v.key === s.key))).toBe(true);
  });
});
