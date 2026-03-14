import type { JSX } from "preact";

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

function powerGlyph(group: "production" | "consumption", subgroup: "potential" | "utilization"): string {
  if (group === "production" && subgroup === "potential") {
    return "◌↑";
  }
  if (group === "production") {
    return "↑";
  }
  if (subgroup === "potential") {
    return "◌↓";
  }
  return "↓";
}

function seriesGlyph(series: ForecastSeries): string {
  if (series.lane === "price") {
    return "$";
  }
  if (series.lane === "soc") {
    return "%";
  }
  const category = classifyPowerSeries(series);
  return powerGlyph(category.group === "unknown" ? "consumption" : category.group, category.subgroup);
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
    >
      <span className="legendSwatch" style={{ background: series.color }} />
      <span className="legendKind">{seriesGlyph(series)}</span>
      <span className="legendText">{series.label}</span>
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
            <div key={elementName} className={`legendElement ${active ? "active" : "dimmed"}`}>
              <button
                type="button"
                className={`legendGroup ${allHidden ? "disabled" : "active"}`}
                onMouseEnter={() => props.onElementHover(elementName)}
                onMouseLeave={() => props.onElementHover(null)}
                onClick={() => props.onToggleElement(elementName)}
              >
                <div className="legendGroupTitle">
                  {elementName}
                  {hiddenCount > 0 ? ` (${elementSeries.length - hiddenCount}/${elementSeries.length})` : ""}
                </div>
              </button>
              <div className="legendSubgroup">{elementSeries.map((series) => renderSeriesItem(series))}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
