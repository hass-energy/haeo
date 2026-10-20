import type { JSX } from "preact";

import { AxesGrid } from "./AxesGrid";
import { OverlayLineLayer } from "./OverlayLineLayer";
import { PowerStackLayer } from "./PowerStackLayer";
import { observer } from "../mobx-observer";
import type { ForecastCardStore } from "../store";

interface ChartSvgProps {
  store: ForecastCardStore;
  onPointerMove: (event: PointerEvent) => void;
  onPointerLeave: () => void;
}

const AxesLayer = observer(function AxesLayer(props: { store: ForecastCardStore }): JSX.Element {
  const { store } = props;
  return (
    <AxesGrid
      locale={store.locale}
      width={store.width}
      height={store.height}
      left={store.margins.left}
      right={store.margins.right}
      top={store.plotTop}
      bottom={store.plotBottom}
      xMin={store.xDomain.min}
      xMax={store.xDomain.max}
      xScale={(time) => store.xScale(time)}
      yScalePower={(value) => store.yScalePower(value)}
      powerMin={store.powerBounds.min}
      powerMax={store.powerBounds.max}
      priceMin={store.priceBounds.min}
      priceMax={store.priceBounds.max}
      yScalePrice={(value) => store.yScalePrice(value)}
    />
  );
});

// Height and gap of each window's strip along the top of the plot
const WINDOW_STRIP_HEIGHT = 4;
const WINDOW_STRIP_GAP = 1;

const WindowLayer = observer(function WindowLayer(props: { store: ForecastCardStore }): JSX.Element {
  const { store } = props;
  const height = store.plotBottom - store.plotTop;
  return (
    <g className="windowLayer">
      {store.windowBands.map((band) => {
        const active = store.highlightedSeries === band.seriesKey || store.focusedLegendSeriesKeys.has(band.seriesKey);
        return (
          <g key={band.key} className={`windowBand ${active ? "active" : ""}`} style={{ color: band.color }}>
            <rect className="windowTint" x={band.x} y={store.plotTop} width={band.width} height={height} />
            <rect
              className="windowStrip"
              x={band.x}
              y={store.plotTop + band.row * (WINDOW_STRIP_HEIGHT + WINDOW_STRIP_GAP)}
              width={band.width}
              height={WINDOW_STRIP_HEIGHT}
            />
          </g>
        );
      })}
    </g>
  );
});

const PowerLayer = observer(function PowerLayer(props: { store: ForecastCardStore }): JSX.Element {
  const { store } = props;
  return (
    <PowerStackLayer
      shapes={store.powerShapes}
      highlightedSeries={store.highlightedSeries}
      hoveredSeriesKeys={store.hoveredPowerSeriesKeys}
      focusedSeriesKeys={store.focusedLegendSeriesKeys}
    />
  );
});

const OverlayLayers = observer(function OverlayLayers(props: { store: ForecastCardStore }): JSX.Element {
  const { store } = props;
  return (
    <>
      <OverlayLineLayer
        paths={store.pricePaths}
        highlightedSeries={store.highlightedSeries}
        focusedSeriesKeys={store.focusedLegendSeriesKeys}
        cssClass="priceLine"
      />

      <OverlayLineLayer
        paths={store.socPaths}
        highlightedSeries={store.highlightedSeries}
        focusedSeriesKeys={store.focusedLegendSeriesKeys}
        cssClass="socLine"
      />
    </>
  );
});

const HoverOverlay = observer(function HoverOverlay(props: { store: ForecastCardStore }): JSX.Element | null {
  const { store } = props;
  const time = store.hoverTimeMs;
  if (time === null) {
    return null;
  }
  const x = store.xScale(time);
  return <line className="hoverLine" x1={x} y1={store.plotTop} x2={x} y2={store.plotBottom} />;
});

const PlotViewport = observer(function PlotViewport(props: { store: ForecastCardStore }): JSX.Element {
  const { store } = props;
  const plotWidth = store.width - store.margins.left - store.margins.right;
  const plotHeight = store.plotBottom - store.plotTop;
  return (
    <svg
      className="plotViewport"
      x={store.margins.left}
      y={store.plotTop}
      width={plotWidth}
      height={plotHeight}
      overflow="hidden"
    >
      <g transform={`translate(${-store.margins.left} ${-store.plotTop})`}>
        <WindowLayer store={store} />
        <PowerLayer store={store} />
        <OverlayLayers store={store} />
        <HoverOverlay store={store} />
      </g>
    </svg>
  );
});

export const ChartSvg = observer(function ChartSvg(props: ChartSvgProps): JSX.Element {
  const { store } = props;

  return (
    <svg
      width={store.width}
      height={store.height}
      onPointerMove={(event) => props.onPointerMove(event as unknown as PointerEvent)}
      onPointerLeave={props.onPointerLeave}
    >
      <AxesLayer store={store} />
      <PlotViewport store={store} />
    </svg>
  );
});
