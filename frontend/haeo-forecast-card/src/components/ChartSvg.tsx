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
      socMin={store.socBounds.min}
      socMax={store.socBounds.max}
      yScalePrice={(value) => store.yScalePrice(value)}
      yScaleSoc={(value) => store.yScaleSoc(value)}
    />
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
  if (store.hoverX === null) {
    return null;
  }
  return <line className="hoverLine" x1={store.hoverX} y1={store.plotTop} x2={store.hoverX} y2={store.plotBottom} />;
});

export const ChartSvg = observer(function ChartSvg(props: ChartSvgProps): JSX.Element {
  const { store } = props;
  const clipId = `haeo-plot-clip-${store.instanceId}`;

  return (
    <svg
      viewBox={`0 0 ${store.width} ${store.height}`}
      height={store.height}
      preserveAspectRatio="none"
      onPointerMove={(event) => props.onPointerMove(event as unknown as PointerEvent)}
      onPointerLeave={props.onPointerLeave}
    >
      <defs>
        <clipPath id={clipId}>
          <rect
            x={store.margins.left}
            y={store.plotTop}
            width={store.width - store.margins.left - store.margins.right}
            height={store.plotBottom - store.plotTop}
          />
        </clipPath>
      </defs>

      <AxesLayer store={store} />

      <g clipPath={`url(#${clipId})`}>
        <PowerLayer store={store} />
        <OverlayLayers store={store} />
      </g>

      <HoverOverlay store={store} />
    </svg>
  );
});
