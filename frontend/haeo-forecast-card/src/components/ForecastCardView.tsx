import type { JSX } from "preact";
import * as mdi from "@mdi/js";

import { ChartSvg } from "./ChartSvg";
import { Legend } from "./Legend";
import { Tooltip } from "./Tooltip";
import { t } from "../i18n";
import { observer } from "../mobx-observer";
import { HORIZON_OPTIONS } from "../store";
import type { ForecastCardStore } from "../store";
import type { HorizonOption } from "../store";

interface ForecastCardViewProps {
  store: ForecastCardStore;
  onPointerMove: (event: PointerEvent) => void;
  onPointerLeave: () => void;
}

function horizonLabel(hours: HorizonOption): string {
  return hours === null ? "All" : `${hours}h`;
}

const CardTitle = observer(function CardTitle(props: { store: ForecastCardStore }): JSX.Element {
  const icons = mdi as Record<string, string>;
  const modeIconPath = icons["mdiSwapVertical"] ?? icons["mdiSwapHorizontal"] ?? icons["mdiSwapVerticalVariant"] ?? "";
  const modeLabel =
    props.store.powerDisplayMode === "opposed"
      ? t(props.store.locale, "legend.mode.opposed")
      : t(props.store.locale, "legend.mode.overlay");
  return (
    <div className="cardHeader">
      <div className="title">{props.store.config.title ?? t(props.store.locale, "card.title.default")}</div>
      <div className="headerControls">
        <div className="horizonSelector">
          {HORIZON_OPTIONS.map((option) => (
            <button
              key={String(option)}
              type="button"
              className={`horizonButton ${props.store.horizonHours === option ? "active" : ""}`}
              onClick={() => props.store.setHorizon(option)}
              title={t(props.store.locale, "header.horizon", { hours: horizonLabel(option) })}
            >
              {horizonLabel(option)}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="modeToggleButton"
          onClick={() => props.store.togglePowerDisplayMode()}
          title={`${t(props.store.locale, "legend.mode")}: ${modeLabel}`}
          aria-label={`${t(props.store.locale, "legend.mode")}: ${modeLabel}`}
        >
          <svg className="modeToggleIcon" viewBox="0 0 24 24" aria-hidden="true">
            <path d={modeIconPath} />
          </svg>
        </button>
      </div>
    </div>
  );
});

const ChartSection = observer(function ChartSection(props: ForecastCardViewProps): JSX.Element {
  return <ChartSvg store={props.store} onPointerMove={props.onPointerMove} onPointerLeave={props.onPointerLeave} />;
});

const LegendSection = observer(function LegendSection(props: { store: ForecastCardStore }): JSX.Element {
  return (
    <Legend
      series={props.store.legendSeries}
      locale={props.store.locale}
      highlightedSeries={props.store.highlightedSeries}
      hoveredElement={props.store.hoveredLegendElement}
      hiddenSeriesKeys={props.store.hiddenSeriesKeys}
      visibilityRevision={props.store.visibilityRevision}
      onHighlight={(key) => {
        props.store.setHighlightedSeriesGroup(null);
        props.store.setHighlightedSeries(key);
      }}
      onHighlightGroup={(keys) => {
        props.store.setHighlightedSeries(null);
        props.store.setHighlightedSeriesGroup(keys);
      }}
      onElementHover={(elementName) => {
        props.store.setHoveredLegendElement(elementName);
      }}
      onToggleSeries={(key) => {
        props.store.toggleSeriesVisibility(key);
      }}
      onToggleElement={(elementName) => {
        props.store.toggleElementVisibility(elementName);
      }}
    />
  );
});

const TooltipSection = observer(function TooltipSection(props: { store: ForecastCardStore }): JSX.Element | null {
  return (
    <Tooltip
      locale={props.store.locale}
      panelTimeMs={props.store.panelTimeMs}
      rows={props.store.tooltipRows}
      totals={props.store.tooltipTotals}
      emphasizedKeys={props.store.tooltipEmphasisKeys}
    />
  );
});

export const ForecastCardView = observer(function ForecastCardView(props: ForecastCardViewProps): JSX.Element {
  return (
    <ha-card>
      <CardTitle store={props.store} />
      <div className="chartRow">
        <div className="chartContainer">
          {props.store.hasData ? (
            <ChartSection
              store={props.store}
              onPointerMove={props.onPointerMove}
              onPointerLeave={props.onPointerLeave}
            />
          ) : (
            <div className="empty">{t(props.store.locale, "card.empty.message")}</div>
          )}
        </div>
        {props.store.hasData && <TooltipSection store={props.store} />}
      </div>
      {props.store.hasData && <LegendSection store={props.store} />}
    </ha-card>
  );
});
