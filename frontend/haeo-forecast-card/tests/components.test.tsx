// @vitest-environment jsdom

import { render } from "preact";
import { afterEach, describe, expect, it } from "vitest";

import { ForecastCardView } from "../src/components/ForecastCardView";
import { Legend } from "../src/components/Legend";
import { scenarioFixture } from "../src/fixtures/scenarioFixture";
import { normalizeSeries } from "../src/series";
import { ForecastCardStore } from "../src/store";

describe("ForecastCardView components", () => {
  const root = document.createElement("div");
  document.body.appendChild(root);

  afterEach(() => {
    render(null, root);
  });

  it("renders chart lanes and legend items", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setHass(scenarioFixture);
    store.setSize(900, 380);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    expect(root.querySelectorAll(".legendItem").length).toBeGreaterThan(0);
    expect(root.querySelectorAll("svg .areaSeries").length).toBeGreaterThan(0);
    expect(root.querySelectorAll("svg .lineSeries").length).toBeGreaterThan(0);
  });

  it("renders tooltip when hover pointer is set", () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setHass(scenarioFixture);
    store.setSize(900, 380);
    store.setPointer(300, 110);

    render(<ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />, root);

    expect(root.querySelector(".tooltip")).toBeTruthy();
    expect(root.querySelectorAll(".tooltipRow").length).toBeGreaterThan(0);
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
    const series = normalizeSeries(scenarioFixture, { type: "custom:haeo-forecast-card" });
    render(
      <Legend
        series={series}
        highlightedSeries={null}
        onHighlight={(key) => {
          hits.push(key);
        }}
      />,
      root
    );
    const firstItem = root.querySelector<HTMLElement>(".legendItem");
    expect(firstItem).toBeTruthy();
    firstItem?.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    firstItem?.dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));
    expect(hits.length).toBeGreaterThanOrEqual(2);
    expect(hits[hits.length - 1]).toBeNull();
  });
});
