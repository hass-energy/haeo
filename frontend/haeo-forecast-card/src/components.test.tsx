import { render } from "preact";
import { afterEach, describe, expect, it } from "vitest";

import { ForecastCardView } from "./components/ForecastCardView";
import { Legend } from "./components/Legend";
import { loadScenarioHassState, withSingleHubRegistry } from "./fixtures/scenarioOutputs";
import { normalizeSeries } from "./series";
import { ForecastCardStore } from "./store";
import type { HassLike } from "./series";

const testFixture: HassLike = withSingleHubRegistry({
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
});

const testCardConfig = {
  type: "custom:haeo-forecast-card" as const,
  hub_entry_id: "hub-alpha",
  entities: ["sensor.grid_import_power", "sensor.grid_import_price", "sensor.battery_soc"],
};

const windowFixture: HassLike = withSingleHubRegistry({
  states: {
    ...testFixture.states,
    "number.pump_run_window": {
      entity_id: "number.pump_run_window",
      attributes: {
        element_name: "Pump",
        element_type: "deferrable_load",
        field_name: "in_window",
        field_type: "availability",
        calendar_projection: "window_active",
        config_mode: "driven",
        friendly_name: "Pump Run window",
        forecast: [
          { time: "2025-10-06T10:50:00.000000+0000", value: 1 },
          { time: "2025-10-06T10:51:00.000000+0000", value: 1 },
          { time: "2025-10-06T10:55:00.000000+0000", value: 0 },
        ],
      },
    },
  },
});

const windowCardConfig = {
  ...testCardConfig,
  entities: [...testCardConfig.entities, "number.pump_run_window"],
};

describe("ForecastCardView components", () => {
  const root = document.createElement("div");
  document.body.appendChild(root);

  afterEach(() => {
    render(null, root);
  });

  it("renders chart lanes and legend items", () => {
    const store = new ForecastCardStore();
    store.setConfig(testCardConfig);
    store.setHass(testFixture);
    store.setSize(900, 380);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    expect(root.querySelectorAll(".legendItem").length).toBeGreaterThan(0);
    expect(root.querySelectorAll("svg .areaSeries").length).toBeGreaterThan(0);
    expect(root.querySelectorAll("svg .lineSeries").length).toBeGreaterThan(0);
  });

  it("renders tooltip when hover pointer is set", () => {
    const store = new ForecastCardStore();
    store.setConfig(testCardConfig);
    store.setHass(testFixture);
    store.setSize(900, 380);
    store.setPointer(300, 110);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    expect(root.querySelector(".tooltip")).toBeTruthy();
    expect(root.querySelectorAll(".tooltipRow").length).toBeGreaterThan(0);
  });

  it.each([
    ["24", false],
    ["12", true],
  ])("formats times with the %s-hour clock from the Home Assistant profile", (timeFormat, showsDayPeriod) => {
    const store = new ForecastCardStore();
    store.setConfig(testCardConfig);
    store.setHass({ ...testFixture, language: "en", locale: { language: "en", time_format: timeFormat } });
    store.setSize(900, 380);
    store.setPointer(300, 110);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    const times = [
      root.querySelector(".tooltipTime")?.textContent ?? "",
      ...Array.from(root.querySelectorAll(".axisTickLabel")).map((label) => label.textContent),
    ].filter((text) => /\d:\d\d/.test(text));
    expect(times.length).toBeGreaterThan(1);
    for (const text of times) {
      expect(/AM|PM/.test(text)).toBe(showsDayPeriod);
    }
  });

  it.each([
    ["DMY", "6/10/2025"],
    ["MDY", "10/6/2025"],
    ["YMD", "2025/10/6"],
  ])("orders the tooltip date by the %s format from the Home Assistant profile", (dateFormat, expectedDate) => {
    const store = new ForecastCardStore();
    store.setConfig(testCardConfig);
    store.setHass({
      ...testFixture,
      language: "en",
      locale: { language: "en", date_format: dateFormat, time_zone: "server" },
      config: { time_zone: "UTC" },
    });
    store.setSize(900, 380);
    store.setPointer(300, 110);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    expect(root.querySelector(".tooltipTime")?.textContent).toMatch(new RegExp(`^${expectedDate}, `));
  });

  it("formats tooltip values with the number format from the Home Assistant profile", () => {
    const store = new ForecastCardStore();
    store.setConfig(testCardConfig);
    store.setHass({ ...testFixture, language: "en", locale: { language: "en", number_format: "decimal_comma" } });
    store.setSize(900, 380);
    store.setPointer(300, 110);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    const values = Array.from(root.querySelectorAll(".tooltipRow")).map((row) => row.textContent);
    expect(values.some((text) => /\d,\d\d/.test(text))).toBe(true);
    expect(values.some((text) => /\d\.\d\d/.test(text))).toBe(false);
  });

  it("shows axis times in the server's time zone when the profile asks for it", () => {
    const labelsFor = (timeZone: string): string[] => {
      const store = new ForecastCardStore();
      store.setConfig(testCardConfig);
      store.setHass({
        ...testFixture,
        language: "en",
        locale: { language: "en", time_format: "24", time_zone: "server" },
        config: { time_zone: timeZone },
      });
      store.setSize(900, 380);
      render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);
      return Array.from(root.querySelectorAll(".axisTickLabel"))
        .map((label) => label.textContent)
        .filter((text) => /^\d\d:\d\d$/.test(text));
    };

    const utc = labelsFor("UTC");
    const tokyo = labelsFor("Asia/Tokyo");
    expect(utc.length).toBeGreaterThan(0);
    // Tokyo is 9 hours ahead of UTC, so every tick label moves 9 hours on
    const shifted = utc.map((label) => {
      const [hours = 0, minutes = 0] = label.split(":").map(Number);
      return `${String((hours + 9) % 24).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
    });
    expect(tokyo).toEqual(shifted);
  });

  it("hides tooltip details from the header toggle", async () => {
    const store = new ForecastCardStore();
    store.setConfig(testCardConfig);
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

  it("renders loading state before hass registry data is available", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card", hub_entry_id: "hub-alpha" });
    store.setSize(800, 300);
    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);
    expect(root.textContent).toContain("Loading HAEO forecast data");
  });

  it("renders hub-not-found when registry data excludes the configured hub", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card", hub_entry_id: "hub-deleted" });
    store.setHass({
      states: {},
      entities: {},
      devices: { "dev-alpha": { config_entries: ["hub-alpha"] } },
    });
    store.setSize(800, 300);
    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);
    expect(root.textContent).toContain("The selected HAEO hub no longer exists");
  });

  it("handles legend enter and leave callbacks", () => {
    const hits: Array<string | null> = [];
    const groups: Array<string | null> = [];
    const toggles: string[] = [];
    const elementToggles: string[] = [];
    const series = normalizeSeries(testFixture, testCardConfig);
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

  it("keeps a buffer's level out of its battery's charge toggle", () => {
    const toggles: string[] = [];
    const series = normalizeSeries(testFixture, testCardConfig);
    const batterySoc = series.find((item) => item.entityId === "sensor.battery_soc")!;
    const reserve = {
      ...batterySoc,
      key: "sensor.reserve_soc:level",
      label: "Reserve level",
      elementType: "buffer" as const,
      direction: "+" as const,
    };
    render(
      <Legend
        series={[...series, reserve]}
        locale="en"
        highlightedSeries={null}
        hoveredElement={null}
        hiddenSeriesKeys={new Set()}
        visibilityRevision={0}
        onHighlight={() => undefined}
        onHighlightGroup={() => undefined}
        onElementHover={() => undefined}
        onToggleSeries={(key) => {
          toggles.push(key);
        }}
        onToggleElement={() => undefined}
      />,
      root
    );

    root.querySelector<HTMLButtonElement>('[title="Toggle Battery Min / max / charge %"]')?.click();
    root.querySelector<HTMLButtonElement>('[title="Reserve level"]')?.click();

    expect(toggles).toEqual([batterySoc.key, reserve.key]);
  });

  it("updates store state from forecast view interactions", () => {
    const store = new ForecastCardStore();
    store.setConfig({ ...testCardConfig });
    store.setHass(testFixture);
    store.setSize(900, 380);
    store.setPointer(300, 120);
    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    const modeButton = root.querySelector<HTMLButtonElement>(".powerModeToggleButton");
    const gridElement = Array.from(root.querySelectorAll(".legendElement")).find((el) =>
      el.textContent.includes("Grid")
    );
    const firstLegendItem = (gridElement?.querySelector(".legendItem") as HTMLButtonElement | null) ?? null;
    const gridElementLabel = gridElement?.querySelector<HTMLButtonElement>(".legendElementLabel") ?? null;
    const horizonSlider = root.querySelector<HTMLInputElement>(".horizonSlider");
    expect(modeButton).toBeTruthy();
    expect(firstLegendItem).toBeTruthy();
    expect(gridElementLabel).toBeTruthy();
    expect(horizonSlider).toBeTruthy();
    modeButton?.click();
    gridElementLabel?.click();
    firstLegendItem?.click();
    firstLegendItem?.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    expect(store.powerDisplayMode).toBe("overlay");
    expect(store.highlightedSeries).toBeTruthy();
    expect(root.querySelector(".tooltipRow.active") || root.querySelector(".tooltip")).toBeTruthy();
  });

  it("updates the horizon from the slider", async () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card", hub_entry_id: "hub-alpha" });
    store.setHass(loadScenarioHassState("scenario2"));
    store.setSize(900, 380);
    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    const horizonValue = root.querySelector(".horizonValue");
    const horizonSlider = root.querySelector<HTMLInputElement>(".horizonSlider");
    expect(horizonValue?.textContent).toMatch(/^3(\.0)?d$/);
    expect(horizonSlider).toBeTruthy();
    if (horizonSlider) {
      horizonSlider.value = "4";
      horizonSlider.dispatchEvent(new InputEvent("input", { bubbles: true }));
    }
    await Promise.resolve();

    expect(store.horizonDurationMs).toBe(4 * 3_600_000);
    expect(root.querySelector(".horizonValue")?.textContent).toBe("4h");
  });

  it("draws open windows as a tint and a strip, stronger when their series is highlighted", () => {
    const store = new ForecastCardStore();
    store.setConfig(windowCardConfig);
    store.setHass(windowFixture);
    store.setSize(900, 380);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    expect(root.querySelectorAll("svg .windowTint")).toHaveLength(1);
    expect(root.querySelectorAll("svg .windowStrip")).toHaveLength(1);
    expect(root.querySelector("svg .windowBand.active")).toBeNull();

    const windowKey = store.windowSeries[0]?.key ?? null;
    store.setHighlightedSeries(windowKey);
    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    expect(root.querySelector("svg .windowBand.active")).toBeTruthy();
  });

  it("lists open windows in the tooltip without a value", () => {
    const store = new ForecastCardStore();
    store.setConfig(windowCardConfig);
    store.setHass(windowFixture);
    store.setSize(900, 380);
    store.setPointer(store.xScale(Date.parse("2025-10-06T10:50:30Z")), 110);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    const row = Array.from(root.querySelectorAll(".tooltipRow")).find((item) =>
      item.textContent.includes("Pump Run window")
    );
    expect(row).toBeTruthy();
    expect(row?.querySelectorAll("span")[2]?.textContent).toBe("");
  });
});
