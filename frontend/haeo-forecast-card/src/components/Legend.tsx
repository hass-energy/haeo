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

  const renderItem = (series: ForecastSeries): JSX.Element => (
    <div
      key={series.key}
      className={`legendItem ${props.highlightedSeries === series.key ? "active" : ""} ${
        props.hiddenSeriesKeys.has(series.key) ? "disabled" : ""
      }`}
      onMouseEnter={() => props.onHighlight(series.key)}
      onMouseLeave={() => props.onHighlight(null)}
      onClick={() => props.onToggleSeries(series.key)}
    >
      <span className="legendSwatch" style={{ background: series.color }} />
      <span className="legendText">{series.label}</span>
    </div>
  );

  const renderSection = (title: string, series: ForecastSeries[]): JSX.Element | null => {
    if (series.length === 0) {
      return null;
    }
    return (
      <div className="legendSubgroup">
        <div className="legendSubgroupTitle">{title}</div>
        {series.map((item) => renderItem(item))}
      </div>
    );
  };

  return (
    <div className="legendWrap">
      <div className="legendControls">
        <button type="button" className="legendModeToggle" onClick={props.onTogglePowerDisplayMode}>
          Mode: {props.powerDisplayMode === "opposed" ? "Opposed" : "Overlay"}
        </button>
      </div>
      <div className="legend">
        <div
          className={`legendGroup ${props.hoveredGroup === null || props.hoveredGroup === "production" ? "active" : "dimmed"}`}
          onMouseEnter={() => props.onGroupHover("production")}
          onMouseLeave={() => props.onGroupHover(null)}
        >
          <div className="legendGroupTitle">Production</div>
          {renderSection("Potential output", productionPotential)}
          {renderSection("Delivered output", productionUtilization)}
        </div>
        <div
          className={`legendGroup ${props.hoveredGroup === null || props.hoveredGroup === "consumption" ? "active" : "dimmed"}`}
          onMouseEnter={() => props.onGroupHover("consumption")}
          onMouseLeave={() => props.onGroupHover(null)}
        >
          <div className="legendGroupTitle">Consumption</div>
          {renderSection("Potential demand", consumptionPotential)}
          {renderSection("Active demand", consumptionUtilization)}
        </div>
        {contextSeries.length > 0 && (
          <div
            className={`legendGroup ${props.hoveredGroup === null || props.hoveredGroup === "reference" ? "active" : "dimmed"}`}
            onMouseEnter={() => props.onGroupHover("reference")}
            onMouseLeave={() => props.onGroupHover(null)}
          >
            <div className="legendGroupTitle">Reference</div>
            <div className="legendSubgroup">{contextSeries.map((series) => renderItem(series))}</div>
          </div>
        )}
      </div>
    </div>
  );
}
