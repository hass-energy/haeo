// @vitest-environment jsdom

import { render } from "preact";
import { afterEach, describe, expect, it } from "vitest";

import { ForecastCardView } from "../src/components/ForecastCardView";
import { Legend } from "../src/components/Legend";
import { normalizeSeries } from "../src/series";
import { ForecastCardStore } from "../src/store";
import type { HassLike } from "../src/series";

const testFixture: HassLike = {
  states: {
    "sensor.grid_import_power": {
      entity_id: "sensor.grid_import_power",
      attributes: {
        element_name: "Grid",
        output_name: "import_power",
        output_type: "power",
        unit_of_measurement: "kW",
        forecast: [
          { time: "2025-10-06T10:50:00.000000+0000", value: 2.2 },
          { time: "2025-10-06T10:51:00.000000+0000", value: 1.8 },
          { time: "2025-10-06T10:55:00.000000+0000", value: 1.0 },
        ],
      },
    },
    "sensor.grid_import_price": {
      entity_id: "sensor.grid_import_price",
      attributes: {
        element_name: "Grid",
        output_name: "import_price",
        output_type: "price",
        unit_of_measurement: "$/kWh",
        forecast: [
          { time: "2025-10-06T10:50:00.000000+0000", value: 0.18 },
          { time: "2025-10-06T10:51:00.000000+0000", value: 0.24 },
          { time: "2025-10-06T10:55:00.000000+0000", value: 0.2 },
        ],
      },
    },
    "sensor.battery_soc": {
      entity_id: "sensor.battery_soc",
      attributes: {
        element_name: "Battery",
        output_name: "state_of_charge",
        output_type: "state_of_charge",
        unit_of_measurement: "%",
        forecast: [
          { time: "2025-10-06T10:50:00.000000+0000", value: 60.2 },
          { time: "2025-10-06T10:51:00.000000+0000", value: 60.9 },
          { time: "2025-10-06T10:55:00.000000+0000", value: 61.5 },
        ],
      },
    },
  },
};

describe("ForecastCardView components", () => {
  const root = document.createElement("div");
  document.body.appendChild(root);

  afterEach(() => {
    render(null, root);
  });

  it("renders chart lanes and legend items", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setHass(testFixture);
    store.setSize(900, 380);

    render(
      <ForecastCardView
        store={store}
        onPointerMove={() => undefined}
        onPointerLeave={() => undefined}
        onStateChange={() => undefined}
      />,
      root
    );

    expect(root.querySelectorAll(".legendItem").length).toBeGreaterThan(0);
    expect(root.querySelectorAll("svg .areaSeries").length).toBeGreaterThan(0);
    expect(root.querySelectorAll("svg .lineSeries").length).toBeGreaterThan(0);
  });

  it("renders tooltip when hover pointer is set", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setHass(testFixture);
    store.setSize(900, 380);
    store.setPointer(300, 110);

    render(
      <ForecastCardView
        store={store}
        onPointerMove={() => undefined}
        onPointerLeave={() => undefined}
        onStateChange={() => undefined}
      />,
      root
    );

    expect(root.querySelector(".tooltip")).toBeTruthy();
    expect(root.querySelectorAll(".tooltipRow").length).toBeGreaterThan(0);
  });

  it("renders empty state when there is no data", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setSize(800, 300);
    render(
      <ForecastCardView
        store={store}
        onPointerMove={() => undefined}
        onPointerLeave={() => undefined}
        onStateChange={() => undefined}
      />,
      root
    );
    expect(root.textContent).toContain("No forecast data found");
  });

  it("handles legend enter and leave callbacks", () => {
    const hits: Array<string | null> = [];
    const groups: Array<string | null> = [];
    const toggles: string[] = [];
    const elementToggles: string[] = [];
    const series = normalizeSeries(testFixture, { type: "custom:haeo-forecast-card" });
    render(
      <Legend
        series={series}
        highlightedSeries={null}
        hoveredElement={null}
        hiddenSeriesKeys={new Set()}
        powerDisplayMode="opposed"
        onHighlight={(key) => {
          hits.push(key);
        }}
        onElementHover={(group) => {
          groups.push(group);
        }}
        onToggleSeries={(key) => {
          toggles.push(key);
        }}
        onToggleElement={(elementName) => {
          elementToggles.push(elementName);
        }}
        onTogglePowerDisplayMode={() => undefined}
      />,
      root
    );
    const firstItem = root.querySelector<HTMLElement>(".legendItem");
    const firstGroup = root.querySelector<HTMLElement>(".legendElementLabel");
    expect(firstItem).toBeTruthy();
    expect(firstGroup).toBeTruthy();
    firstItem?.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    firstItem?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    firstItem?.dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));
    root.querySelector<HTMLElement>(".legendElement")?.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    root.querySelector<HTMLElement>(".legendElement")?.dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));
    expect(hits.length).toBeGreaterThanOrEqual(2);
    expect(hits[hits.length - 1]).toBeNull();
    expect(toggles.length).toBe(1);
    expect(groups.length).toBeGreaterThanOrEqual(2);
    expect(groups[groups.length - 1]).toBeNull();
    expect(elementToggles.length).toBeGreaterThanOrEqual(0);
  });

  it("triggers state changes from forecast view interactions", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card", animation_mode: "off" });
    store.setHass(testFixture);
    store.setSize(900, 380);
    store.setPointer(300, 120);
    let updates = 0;
    render(
      <ForecastCardView
        store={store}
        onPointerMove={() => undefined}
        onPointerLeave={() => undefined}
        onStateChange={() => {
          updates += 1;
        }}
      />,
      root
    );

    const modeButton = root.querySelector<HTMLButtonElement>(".legendModeToggle");
    const firstLegendItem = root.querySelector<HTMLButtonElement>(".legendItem");
    expect(modeButton).toBeTruthy();
    expect(firstLegendItem).toBeTruthy();
    modeButton?.click();
    firstLegendItem?.click();
    firstLegendItem?.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    expect(updates).toBeGreaterThanOrEqual(3);
    expect(root.querySelector(".tooltipRow.active") || root.querySelector(".tooltip")).toBeTruthy();
  });
});
