import { describe, expect, it } from "vitest";

import { legendSeriesOrder, seriesIconPath, seriesTooltip } from "./legend-helpers";
import type { ForecastSeries } from "./types";

function makeSeries(overrides: Partial<ForecastSeries> = {}): ForecastSeries {
  return {
    key: "test:power",
    entityId: "sensor.test",
    label: "Test",
    elementName: "Test",
    elementType: "load",
    outputName: "power",
    outputType: "power",
    direction: "-",
    sourceRole: "output",
    plotStream: null,
    plotPriority: null,
    lane: "power",
    drawType: "step",
    unit: "kW",
    color: "#333",
    times: new Float64Array([0]),
    values: new Float64Array([1]),
    ...overrides,
  };
}

describe("seriesIconPath", () => {
  it("returns an import price icon for import price series", () => {
    const series = makeSeries({ lane: "price", outputName: "import_price" });
    expect(seriesIconPath(series)).toBeTruthy();
  });

  it("returns an export price icon for export price series", () => {
    const series = makeSeries({ lane: "price", outputName: "export_price" });
    expect(seriesIconPath(series)).toBeTruthy();
  });

  it("returns a battery icon for SOC series", () => {
    const series = makeSeries({ lane: "soc", outputName: "soc" });
    expect(seriesIconPath(series)).toBeTruthy();
  });

  it("returns a solar icon for solar elements", () => {
    const series = makeSeries({ elementName: "Solar", elementType: "solar", direction: "+" });
    expect(seriesIconPath(series)).toBeTruthy();
  });

  it("returns a battery icon for battery elements", () => {
    const series = makeSeries({ elementName: "Battery", elementType: "battery", direction: "+" });
    expect(seriesIconPath(series)).toBeTruthy();
  });

  it("returns a consumption icon for import series", () => {
    const series = makeSeries({ outputName: "import_power", direction: "-" });
    expect(seriesIconPath(series)).toBeTruthy();
  });

  it("returns an export icon for export series", () => {
    const series = makeSeries({ outputName: "export_power", direction: "+" });
    expect(seriesIconPath(series)).toBeTruthy();
  });

  it("returns fallback for unknown series type", () => {
    const series = makeSeries({ lane: "other", outputName: "unknown", direction: null });
    expect(seriesIconPath(series)).toBeTruthy();
  });
});

describe("seriesTooltip", () => {
  it("returns import price label for import price series", () => {
    const series = makeSeries({ lane: "price", outputName: "import_price", label: "Grid" });
    expect(seriesTooltip(series, "en")).toContain("Grid");
    expect(seriesTooltip(series, "en")).toContain("import");
  });

  it("returns export price label for export price series", () => {
    const series = makeSeries({ lane: "price", outputName: "export_price", label: "Grid" });
    expect(seriesTooltip(series, "en")).toContain("export");
  });

  it("returns produced label for production power", () => {
    const series = makeSeries({ direction: "+", label: "Solar" });
    expect(seriesTooltip(series, "en")).toContain("produced");
  });

  it("returns consumed label for consumption power", () => {
    const series = makeSeries({ direction: "-", label: "Load" });
    expect(seriesTooltip(series, "en")).toContain("consumed");
  });

  it("returns raw label for non-power non-price series", () => {
    const series = makeSeries({ lane: "soc", label: "Battery SOC" });
    expect(seriesTooltip(series, "en")).toBe("Battery SOC");
  });
});

describe("legendSeriesOrder", () => {
  it("ranks production utilization before production potential", () => {
    const prod = makeSeries({ direction: "+" });
    const potential = makeSeries({ direction: "+", sourceRole: "forecast" });
    expect(legendSeriesOrder(prod)).toBeLessThan(legendSeriesOrder(potential));
  });

  it("ranks power before price before SOC", () => {
    const power = makeSeries({ lane: "power" });
    const price = makeSeries({ lane: "price" });
    const soc = makeSeries({ lane: "soc" });
    expect(legendSeriesOrder(power)).toBeLessThan(legendSeriesOrder(price));
    expect(legendSeriesOrder(price)).toBeLessThan(legendSeriesOrder(soc));
  });
});
