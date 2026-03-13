import type { JSX } from "preact";

import { AxesGrid } from "./AxesGrid";
import { OverlayLineLayer } from "./OverlayLineLayer";
import { PowerStackLayer } from "./PowerStackLayer";
import type { ForecastCardStore } from "../store";

interface ChartSvgProps {
  store: ForecastCardStore;
  onPointerMove: (event: PointerEvent) => void;
  onPointerLeave: () => void;
}

export function ChartSvg(props: ChartSvgProps): JSX.Element {
  const { store } = props;

  return (
    <svg
      viewBox={`0 0 ${store.width} ${store.height}`}
      height={store.height}
      onPointerMove={(event) => props.onPointerMove(event as unknown as PointerEvent)}
      onPointerLeave={props.onPointerLeave}
    >
      <AxesGrid
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
      />

      <PowerStackLayer
        seriesList={store.powerSeries}
        highlightedSeries={store.highlightedSeries}
        xScale={(time) => store.xScale(time)}
        yScalePower={(value) => store.yScalePower(value)}
      />

      <OverlayLineLayer
        seriesList={store.priceSeries}
        highlightedSeries={store.highlightedSeries}
        xScale={(time) => store.xScale(time)}
        yScale={(value) => store.yScalePrice(value)}
        cssClass="priceLine"
        forceStep={true}
      />

      <OverlayLineLayer
        seriesList={store.socSeries}
        highlightedSeries={store.highlightedSeries}
        xScale={(time) => store.xScale(time)}
        yScale={(value) => store.yScaleSoc(value)}
        cssClass="socLine"
      />

      {store.hoverX !== null && (
        <line className="hoverLine" x1={store.hoverX} y1={store.plotTop} x2={store.hoverX} y2={store.plotBottom} />
      )}
    </svg>
  );
}
