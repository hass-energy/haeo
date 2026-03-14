import type { JSX } from "preact";
import * as mdi from "@mdi/js";

import { classifyPowerSeries } from "../power-series-classification";
import type { ForecastSeries, PowerDisplayMode } from "../types";

interface LegendProps {
  series: ForecastSeries[];
  highlightedSeries: string | null;
  hoveredElement: string | null;
  hiddenSeriesKeys: Set<string>;
  powerDisplayMode: PowerDisplayMode;
  onHighlight: (key: string | null) => void;
  onElementHover: (elementName: string | null) => void;
  onToggleSeries: (key: string) => void;
  onToggleElement: (elementName: string) => void;
  onTogglePowerDisplayMode: () => void;
}

function seriesIconPath(series: ForecastSeries): string {
  const icons = mdi as Record<string, string>;
  const fallback = icons["mdiChartLine"] ?? "";
  if (series.lane === "price" || series.outputName.includes("price")) {
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

function MdiIcon(props: { path: string }): JSX.Element {
  return (
    <svg className="legendIcon" viewBox="0 0 24 24" aria-hidden="true">
      <path d={props.path} />
    </svg>
  );
}

export function Legend(props: LegendProps): JSX.Element {
  const byElement = new Map<string, ForecastSeries[]>();
  for (const series of props.series) {
    const key = series.elementName;
    const list = byElement.get(key) ?? [];
    list.push(series);
    byElement.set(key, list);
  }
  const elements = [...byElement.entries()].sort((a, b) => a[0].localeCompare(b[0]));

  const renderSeriesItem = (series: ForecastSeries): JSX.Element => (
    <button
      type="button"
      key={series.key}
      className={`legendItem ${props.highlightedSeries === series.key ? "active" : ""} ${
        props.hiddenSeriesKeys.has(series.key) ? "disabled" : ""
      }`}
      onMouseEnter={() => props.onHighlight(series.key)}
      onMouseLeave={() => props.onHighlight(null)}
      onClick={() => props.onToggleSeries(series.key)}
      title={series.label}
      style={{ borderColor: series.color, color: series.color }}
    >
      <MdiIcon path={seriesIconPath(series)} />
    </button>
  );

  return (
    <div className="legendWrap">
      <div className="legendControls">
        <button type="button" className="legendModeToggle" onClick={props.onTogglePowerDisplayMode}>
          Mode: {props.powerDisplayMode === "opposed" ? "Opposed" : "Overlay"}
        </button>
      </div>
      <div className="legend">
        {elements.map(([elementName, elementSeries]) => {
          const hiddenCount = elementSeries.filter((series) => props.hiddenSeriesKeys.has(series.key)).length;
          const allHidden = hiddenCount === elementSeries.length;
          const active = props.hoveredElement === null || props.hoveredElement === elementName;
          return (
            <div
              key={elementName}
              className={`legendElement ${active ? "active" : "dimmed"} ${allHidden ? "disabled" : ""}`}
              onMouseEnter={() => props.onElementHover(elementName)}
              onMouseLeave={() => props.onElementHover(null)}
            >
              <div className="legendElementMain">
                <button
                  type="button"
                  className="legendElementLabel"
                  onClick={() => props.onToggleElement(elementName)}
                  title={`Toggle ${elementName} series`}
                >
                  <span className="legendGroupTitle">{elementName}</span>
                </button>
                <div className="legendIconRow">{elementSeries.map((series) => renderSeriesItem(series))}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
