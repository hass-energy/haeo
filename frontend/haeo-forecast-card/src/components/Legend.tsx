import type { JSX } from "preact";

import { classifyPowerSeries } from "../power-series-classification";
import type { ForecastSeries, PowerDisplayMode } from "../types";

interface LegendProps {
  series: ForecastSeries[];
  highlightedSeries: string | null;
  hoveredGroup: "production" | "consumption" | "reference" | null;
  hiddenSeriesKeys: Set<string>;
  powerDisplayMode: PowerDisplayMode;
  onHighlight: (key: string | null) => void;
  onGroupHover: (group: "production" | "consumption" | "reference" | null) => void;
  onToggleSeries: (key: string) => void;
  onTogglePowerDisplayMode: () => void;
}

function categoryGlyph(group: "production" | "consumption", subgroup: "potential" | "utilization"): string {
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

export function Legend(props: LegendProps): JSX.Element {
  const productionPotential: ForecastSeries[] = [];
  const productionUtilization: ForecastSeries[] = [];
  const consumptionPotential: ForecastSeries[] = [];
  const consumptionUtilization: ForecastSeries[] = [];
  const contextSeries: ForecastSeries[] = [];

  for (const series of props.series) {
    if (series.lane !== "power") {
      contextSeries.push(series);
      continue;
    }
    const category = classifyPowerSeries(series);
    if (category.group === "production") {
      if (category.subgroup === "potential") {
        productionPotential.push(series);
      } else {
        productionUtilization.push(series);
      }
      continue;
    }
    if (category.group === "consumption") {
      if (category.subgroup === "potential") {
        consumptionPotential.push(series);
      } else {
        consumptionUtilization.push(series);
      }
      continue;
    }
    consumptionUtilization.push(series);
  }

  const renderItem = (
    series: ForecastSeries,
    group: "production" | "consumption",
    subgroup: "potential" | "utilization"
  ): JSX.Element => (
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
      <span className="legendKind" title={`${group} ${subgroup}`}>
        {categoryGlyph(group, subgroup)}
      </span>
      <span className="legendText">{series.label}</span>
    </button>
  );

  const renderSection = (
    title: string,
    series: ForecastSeries[],
    group: "production" | "consumption",
    subgroup: "potential" | "utilization"
  ): JSX.Element | null => {
    if (series.length === 0) {
      return null;
    }
    return (
      <div className="legendSubgroup">
        <div className="legendSubgroupTitle">{title}</div>
        {series.map((item) => renderItem(item, group, subgroup))}
      </div>
    );
  };

  const renderReferenceItem = (series: ForecastSeries): JSX.Element => (
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
      <span className="legendKind">•</span>
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
        <div className="legendGroups">
          <button
            type="button"
            className={`legendGroup ${props.hoveredGroup === null || props.hoveredGroup === "production" ? "active" : "dimmed"}`}
            onMouseEnter={() => props.onGroupHover("production")}
            onMouseLeave={() => props.onGroupHover(null)}
          >
            <div className="legendGroupTitle">Production</div>
          </button>
          <button
            type="button"
            className={`legendGroup ${props.hoveredGroup === null || props.hoveredGroup === "consumption" ? "active" : "dimmed"}`}
            onMouseEnter={() => props.onGroupHover("consumption")}
            onMouseLeave={() => props.onGroupHover(null)}
          >
            <div className="legendGroupTitle">Consumption</div>
          </button>
          {contextSeries.length > 0 && (
            <button
              type="button"
              className={`legendGroup ${props.hoveredGroup === null || props.hoveredGroup === "reference" ? "active" : "dimmed"}`}
              onMouseEnter={() => props.onGroupHover("reference")}
              onMouseLeave={() => props.onGroupHover(null)}
            >
              <div className="legendGroupTitle">Reference</div>
            </button>
          )}
        </div>
        {renderSection("Potential output", productionPotential, "production", "potential")}
        {renderSection("Delivered output", productionUtilization, "production", "utilization")}
        {renderSection("Potential demand", consumptionPotential, "consumption", "potential")}
        {renderSection("Active demand", consumptionUtilization, "consumption", "utilization")}
        {contextSeries.length > 0 && (
          <div className="legendSubgroup">{contextSeries.map((series) => renderReferenceItem(series))}</div>
        )}
      </div>
    </div>
  );
}
