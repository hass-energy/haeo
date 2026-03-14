import type { JSX } from "preact";

import { ChartSvg } from "./ChartSvg";
import { Legend } from "./Legend";
import { Tooltip } from "./Tooltip";
import { t } from "../i18n";
import { observer } from "../mobx-observer";
import type { ForecastCardStore } from "../store";

interface ForecastCardViewProps {
  store: ForecastCardStore;
  onPointerMove: (event: PointerEvent) => void;
  onPointerLeave: () => void;
}

const CardTitle = observer(function CardTitle(props: { store: ForecastCardStore }): JSX.Element {
  return <div className="title">{props.store.config.title ?? t(props.store.locale, "card.title.default")}</div>;
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
      powerDisplayMode={props.store.powerDisplayMode}
      onHighlight={(key) => {
        props.store.setHighlightedSeries(key);
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
      onTogglePowerDisplayMode={() => {
        props.store.togglePowerDisplayMode();
      }}
    />
  );
});

const TooltipSection = observer(function TooltipSection(props: { store: ForecastCardStore }): JSX.Element | null {
  return (
    <Tooltip
      locale={props.store.locale}
      hoverTimeMs={props.store.hoverTimeMs}
      rows={props.store.tooltipRows}
      totals={props.store.tooltipTotals}
      emphasizedKeys={props.store.tooltipEmphasisKeys}
    />
  );
});

export const ForecastCardView = observer(function ForecastCardView(props: ForecastCardViewProps): JSX.Element {
  if (!props.store.hasData) {
    return (
      <ha-card>
        <CardTitle store={props.store} />
        <div className="empty">{t(props.store.locale, "card.empty.message")}</div>
      </ha-card>
    );
  }

  return (
    <ha-card>
      <CardTitle store={props.store} />
      <ChartSection store={props.store} onPointerMove={props.onPointerMove} onPointerLeave={props.onPointerLeave} />
      <LegendSection store={props.store} />
      <TooltipSection store={props.store} />
    </ha-card>
  );
});
