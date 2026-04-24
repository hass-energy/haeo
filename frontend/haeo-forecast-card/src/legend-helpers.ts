import * as mdi from "@mdi/js";

import { classifyPowerSeries } from "./power-series-classification";
import type { ForecastSeries } from "./types";

export function seriesIconPath(series: ForecastSeries): string {
  const icons = mdi as Record<string, string>;
  const fallback = icons["mdiChartLine"] ?? "";
  if (series.lane === "price" || series.outputName.includes("price")) {
    const output = series.outputName.toLowerCase();
    if (output.includes("import")) {
      return icons["mdiCashPlus"] ?? icons["mdiCurrencyUsd"] ?? fallback;
    }
    if (output.includes("export")) {
      return icons["mdiCashMinus"] ?? icons["mdiCurrencyUsd"] ?? fallback;
    }
    return icons["mdiCurrencyUsd"] ?? fallback;
  }
  if (series.lane === "soc") {
    return icons["mdiBatteryMedium"] ?? fallback;
  }
  const output = series.outputName.toLowerCase();
  const element = series.elementName.toLowerCase();
  const category = classifyPowerSeries(series);
  if (element.includes("solar")) {
    return category.subgroup === "potential"
      ? (icons["mdiWeatherSunnyAlert"] ?? fallback)
      : (icons["mdiSolarPowerVariant"] ?? icons["mdiWeatherSunny"] ?? fallback);
  }
  if (element.includes("battery")) {
    return category.group === "production"
      ? (icons["mdiBatteryArrowUp"] ?? icons["mdiBatteryPlus"] ?? fallback)
      : (icons["mdiBatteryArrowDown"] ?? icons["mdiBatteryMinus"] ?? fallback);
  }
  if (output.includes("import") || category.group === "consumption") {
    return category.subgroup === "potential"
      ? (icons["mdiArrowDownBoldCircleOutline"] ?? fallback)
      : (icons["mdiArrowDownBoldCircle"] ?? fallback);
  }
  if (output.includes("export") || category.group === "production") {
    return category.subgroup === "potential"
      ? (icons["mdiArrowUpBoldCircleOutline"] ?? fallback)
      : (icons["mdiArrowUpBoldCircle"] ?? fallback);
  }
  return fallback;
}

export function seriesTooltip(series: ForecastSeries, _locale: string): string {
  return series.label;
}

export function legendSeriesOrder(series: ForecastSeries): number {
  if (series.lane === "power") {
    const c = classifyPowerSeries(series);
    if (c.group === "production" && c.subgroup === "utilization") return 0;
    if (c.group === "production" && c.subgroup === "potential") return 1;
    if (c.group === "consumption" && c.subgroup === "utilization") return 2;
    if (c.group === "consumption" && c.subgroup === "potential") return 3;
    return 4;
  }
  if (series.lane === "price") return 5;
  if (series.lane === "soc") return 6;
  return 7;
}
