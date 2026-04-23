import type { JSX } from "preact";
import * as mdi from "@mdi/js";

import { t } from "../i18n";
import { legendSeriesOrder, seriesIconPath, seriesTooltip } from "../legend-helpers";
import type { ForecastSeries } from "../types";

interface LegendProps {
  series: ForecastSeries[];
  locale: string;
  highlightedSeries: string | null;
  hoveredElement: string | null;
  hiddenSeriesKeys: Set<string>;
  visibilityRevision: number;
  onHighlight: (key: string | null) => void;
  onHighlightGroup: (keys: string[] | null) => void;
  onElementHover: (elementName: string | null) => void;
  onToggleSeries: (key: string) => void;
  onToggleElement: (elementName: string) => void;
}

function MdiIcon(props: { path: string }): JSX.Element {
  return (
    <svg className="legendIcon" viewBox="0 0 24 24" aria-hidden="true">
      <path d={props.path} />
    </svg>
  );
}

function LegendView(props: LegendProps): JSX.Element {
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
      title={seriesTooltip(series, props.locale)}
      style={{ borderColor: series.color, color: series.color }}
    >
      <MdiIcon path={seriesIconPath(series)} />
    </button>
  );

  const toggleSeriesGroup = (seriesGroup: ForecastSeries[]): void => {
    if (seriesGroup.length === 0) {
      return;
    }
    const allHidden = seriesGroup.every((series) => props.hiddenSeriesKeys.has(series.key));
    for (const series of seriesGroup) {
      const isHidden = props.hiddenSeriesKeys.has(series.key);
      const shouldToggle = allHidden ? isHidden : !isHidden;
      if (shouldToggle) {
        props.onToggleSeries(series.key);
      }
    }
  };

  const renderBatteryGroupItem = (
    seriesGroup: ForecastSeries[],
    elementName: string,
    groupKey: string,
    groupLabel: string,
    iconPath: string
  ): JSX.Element | null => {
    if (seriesGroup.length === 0) {
      return null;
    }
    const allHidden = seriesGroup.every((series) => props.hiddenSeriesKeys.has(series.key));
    const firstVisibleSeries = seriesGroup.find((series) => !props.hiddenSeriesKeys.has(series.key));
    const color = firstVisibleSeries?.color ?? seriesGroup[0]?.color ?? "var(--haeo-text)";
    return (
      <button
        type="button"
        key={`${elementName}:${groupKey}`}
        className={`legendItem ${allHidden ? "disabled" : ""}`}
        onMouseEnter={() => props.onHighlightGroup(seriesGroup.map((series) => series.key))}
        onMouseLeave={() => props.onHighlightGroup(null)}
        onClick={() => toggleSeriesGroup(seriesGroup)}
        title={t(props.locale, "legend.group.toggle", {
          element: elementName,
          group: groupLabel,
        })}
        style={{ borderColor: color, color }}
      >
        <MdiIcon path={iconPath} />
      </button>
    );
  };

  return (
    <div className="legendWrap">
      <div className="legend">
        {elements.map(([elementName, elementSeries]) => {
          const sortedSeries = [...elementSeries].sort((a, b) => {
            const byLane = legendSeriesOrder(a) - legendSeriesOrder(b);
            return byLane !== 0 ? byLane : a.label.localeCompare(b.label);
          });
          const hiddenCount = elementSeries.filter((series) => props.hiddenSeriesKeys.has(series.key)).length;
          const allHidden = hiddenCount === elementSeries.length;
          const active = props.hoveredElement === null || props.hoveredElement === elementName;
          const isBatteryElement = elementSeries.some((series) => series.elementType === "battery");
          const icons = mdi as Record<string, string>;
          const batterySocSeriesGroup = isBatteryElement ? sortedSeries.filter((series) => series.lane === "soc") : [];
          const batteryNonSocSeries = isBatteryElement ? sortedSeries.filter((series) => series.lane !== "soc") : [];
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
                  title={t(props.locale, "legend.toggle.element", { element: elementName })}
                >
                  <span className="legendGroupTitle">{elementName}</span>
                </button>
                <div className="legendIconRow">
                  {isBatteryElement ? (
                    <>
                      {batteryNonSocSeries.map((series) => renderSeriesItem(series))}
                      {renderBatteryGroupItem(
                        batterySocSeriesGroup,
                        elementName,
                        "battery-soc",
                        t(props.locale, "legend.group.battery_soc"),
                        icons["mdiBatteryMedium"] ?? icons["mdiBattery"] ?? ""
                      )}
                    </>
                  ) : (
                    sortedSeries.map((series) => renderSeriesItem(series))
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const Legend = LegendView;
