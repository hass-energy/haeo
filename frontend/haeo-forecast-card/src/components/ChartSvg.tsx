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
  const clipId = "haeo-plot-clip";

  return (
    <svg
      viewBox={`0 0 ${store.width} ${store.height}`}
      height={store.height}
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
        yScalePrice={(value) => store.yScalePrice(value)}
        yScaleSoc={(value) => store.yScaleSoc(value)}
      />

      <g clipPath={`url(#${clipId})`}>
        <PowerStackLayer
          shapes={store.powerShapes}
          highlightedSeries={store.highlightedSeries}
          hoveredSeriesKeys={store.hoveredPowerSeriesKeys}
          focusedSeriesKeys={store.focusedElementSeriesKeys}
        />

        <OverlayLineLayer
          paths={store.pricePaths}
          highlightedSeries={store.highlightedSeries}
          focusedSeriesKeys={store.focusedElementSeriesKeys}
          cssClass="priceLine"
        />

        <OverlayLineLayer
          paths={store.socPaths}
          highlightedSeries={store.highlightedSeries}
          focusedSeriesKeys={store.focusedElementSeriesKeys}
          cssClass="socLine"
        />
      </g>

      {store.hoverX !== null && (
        <line className="hoverLine" x1={store.hoverX} y1={store.plotTop} x2={store.hoverX} y2={store.plotBottom} />
      )}
    </svg>
  );
}
