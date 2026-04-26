import type { JSX } from "preact";
import * as mdi from "@mdi/js";

import { ChartSvg } from "./ChartSvg";
import { Legend } from "./Legend";
import { Tooltip } from "./Tooltip";
import { t } from "../i18n";
import { observer } from "../mobx-observer";
import { formatHorizonDuration } from "../store";
import type { ForecastCardStore } from "../store";
import type { HorizonOption } from "../store";

interface ForecastCardViewProps {
  store: ForecastCardStore;
  onPointerMove: (event: PointerEvent) => void;
  onPointerLeave: () => void;
}

function horizonLabel(store: ForecastCardStore, option: HorizonOption): string {
  return formatHorizonDuration(option ?? store.fullXDomain.max - store.fullXDomain.min);
}

function horizonIndex(store: ForecastCardStore): number {
  return Math.max(
    0,
    store.horizonOptions.findIndex((option) => option === store.horizonDurationMs)
  );
}

const CardTitle = observer(function CardTitle(props: { store: ForecastCardStore }): JSX.Element {
  const icons = mdi as Record<string, string>;
  const modeIconPath = icons["mdiSwapVertical"] ?? icons["mdiSwapHorizontal"] ?? icons["mdiSwapVerticalVariant"] ?? "";
  const tooltipIconPath = props.store.tooltipVisible
    ? (icons["mdiInformationOutline"] ?? icons["mdiEyeOutline"] ?? "")
    : (icons["mdiInformationOffOutline"] ?? icons["mdiEyeOffOutline"] ?? "");
  const modeLabel =
    props.store.powerDisplayMode === "opposed"
      ? t(props.store.locale, "legend.mode.opposed")
      : t(props.store.locale, "legend.mode.overlay");
  const tooltipLabel = props.store.tooltipVisible
    ? t(props.store.locale, "tooltip.visibility.hide")
    : t(props.store.locale, "tooltip.visibility.show");
  const selectedHorizonIndex = horizonIndex(props.store);
  const selectedHorizonLabel = horizonLabel(props.store, props.store.horizonDurationMs);
  return (
    <div className="cardHeader">
      <div className="title">{props.store.config.title ?? t(props.store.locale, "card.title.default")}</div>
      <div className="headerControls">
        <div
          className="horizonSelector"
          title={t(props.store.locale, "header.horizon", { hours: selectedHorizonLabel })}
        >
          <span className="horizonValue">{selectedHorizonLabel}</span>
          <input
            className="horizonSlider"
            type="range"
            min={0}
            max={props.store.horizonOptions.length - 1}
            step={1}
            value={selectedHorizonIndex}
            aria-label={t(props.store.locale, "header.horizon", { hours: selectedHorizonLabel })}
            onInput={(event) => {
              const index = Number(event.currentTarget.value);
              props.store.setHorizon(props.store.horizonOptions[index] ?? null);
            }}
          />
        </div>
        <button
          type="button"
          className="modeToggleButton tooltipToggleButton"
          onClick={() => props.store.toggleTooltipVisibility()}
          title={tooltipLabel}
          aria-label={tooltipLabel}
          aria-pressed={props.store.tooltipVisible}
        >
          <svg className="modeToggleIcon" viewBox="0 0 24 24" aria-hidden="true">
            <path d={tooltipIconPath} />
          </svg>
        </button>
        <button
          type="button"
          className="modeToggleButton powerModeToggleButton"
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
  if (!props.store.tooltipVisible) {
    return null;
  }
  return (
    <Tooltip
      locale={props.store.locale}
      panelTimeMs={props.store.panelTimeMs}
      rows={props.store.tooltipRows}
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
        {props.store.hasData && props.store.tooltipVisible && <TooltipSection store={props.store} />}
      </div>
      {props.store.hasData && <LegendSection store={props.store} />}
    </ha-card>
  );
});
