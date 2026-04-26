import { render } from "preact";
import { afterEach, describe, expect, it } from "vitest";

import { ForecastCardView } from "./components/ForecastCardView";
import { Legend } from "./components/Legend";
import { normalizeSeries } from "./series";
import { ForecastCardStore } from "./store";
import type { HassLike } from "./series";

const testFixture: HassLike = {
  states: {
    "sensor.grid_import_power": {
      entity_id: "sensor.grid_import_power",
      attributes: {
        element_name: "Grid",
        element_type: "grid",
        output_name: "import_power",
        field_type: "power",
        direction: "-",
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
        element_type: "grid",
        output_name: "import_price",
        field_type: "price",
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
        element_type: "battery",
        output_name: "state_of_charge",
        field_type: "state_of_charge",
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

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

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

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    expect(root.querySelector(".tooltip")).toBeTruthy();
    expect(root.querySelectorAll(".tooltipRow").length).toBeGreaterThan(0);
  });

  it("hides tooltip details from the header toggle", async () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setHass(testFixture);
    store.setSize(900, 380);
    store.setPointer(300, 110);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    const tooltipButton = root.querySelector<HTMLButtonElement>(".tooltipToggleButton");
    expect(tooltipButton).toBeTruthy();
    expect(root.querySelector(".tooltip")).toBeTruthy();
    tooltipButton?.click();
    expect(store.tooltipVisible).toBe(false);
    await Promise.resolve();
    expect(root.querySelector(".tooltip")).toBeNull();
  });

  it("renders empty state when there is no data", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setSize(800, 300);
    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);
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
        locale="en"
        highlightedSeries={null}
        hoveredElement={null}
        hiddenSeriesKeys={new Set()}
        visibilityRevision={0}
        onHighlight={(key) => {
          hits.push(key);
        }}
        onHighlightGroup={() => undefined}
        onElementHover={(group) => {
          groups.push(group);
        }}
        onToggleSeries={(key) => {
          toggles.push(key);
        }}
        onToggleElement={(elementName) => {
          elementToggles.push(elementName);
        }}
      />,
      root
    );
    const gridElement = Array.from(root.querySelectorAll(".legendElement")).find((el) =>
      el.textContent.includes("Grid")
    );
    const firstItem = (gridElement?.querySelector(".legendItem") as HTMLElement | null) ?? null;
    const firstGroup = root.querySelector<HTMLElement>(".legendElementLabel");
    expect(firstItem).toBeTruthy();
    expect(firstGroup).toBeTruthy();
    firstItem?.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    firstItem?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    firstItem?.dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));
    firstGroup?.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    firstGroup?.dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));
    expect(hits.length).toBeGreaterThanOrEqual(2);
    expect(hits[hits.length - 1]).toBeNull();
    expect(toggles.length).toBe(1);
    expect(groups.length).toBeGreaterThanOrEqual(2);
    expect(groups[groups.length - 1]).toBeNull();
    expect(elementToggles.length).toBeGreaterThanOrEqual(0);
  });

  it("updates store state from forecast view interactions", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card", animation_mode: "off" });
    store.setHass(testFixture);
    store.setSize(900, 380);
    store.setPointer(300, 120);
    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    const modeButton = root.querySelector<HTMLButtonElement>(".powerModeToggleButton");
    const gridElement = Array.from(root.querySelectorAll(".legendElement")).find((el) =>
      el.textContent.includes("Grid")
    );
    const firstLegendItem = (gridElement?.querySelector(".legendItem") as HTMLButtonElement | null) ?? null;
    const horizonSlider = root.querySelector<HTMLInputElement>(".horizonSlider");
    expect(modeButton).toBeTruthy();
    expect(firstLegendItem).toBeTruthy();
    expect(horizonSlider).toBeTruthy();
    modeButton?.click();
    firstLegendItem?.click();
    firstLegendItem?.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    expect(store.powerDisplayMode).toBe("overlay");
    expect(store.highlightedSeries).toBeTruthy();
    expect(root.querySelector(".tooltipRow.active") || root.querySelector(".tooltip")).toBeTruthy();
  });
});
