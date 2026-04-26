import type { JSX } from "preact";
import { useLayoutEffect, useRef } from "preact/hooks";

import { ForecastCardView } from "./ForecastCardView";
import type { ForecastCardStore } from "../store";

interface ResponsiveStoryFrameProps {
  store: ForecastCardStore;
  initialPointer?: { x: number; y: number };
  height?: string;
  showChartBounds?: boolean;
}

export function ResponsiveStoryFrame(props: ResponsiveStoryFrameProps): JSX.Element {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) {
      return;
    }
    const chartContainer = element.querySelector<HTMLElement>(".chartContainer");
    const updateSize = (): void => {
      const cardRect = element.getBoundingClientRect();
      const chartRect = chartContainer?.getBoundingClientRect();
      const cardWidth = cardRect.width > 0 ? cardRect.width : props.store.cardWidth;
      const chartWidth = chartRect && chartRect.width > 0 ? chartRect.width : cardWidth;
      if (chartWidth <= 0) {
        return;
      }
      const chartHeight =
        chartRect && chartRect.height > 0 ? chartRect.height : props.store.responsiveHeight(cardWidth);
      props.store.setSize(chartWidth, chartHeight, cardWidth);
      if (props.initialPointer) {
        props.store.setPointer(props.initialPointer.x, props.initialPointer.y);
      }
    };
    const observer = new ResizeObserver(() => {
      updateSize();
    });
    observer.observe(element);
    if (chartContainer) {
      observer.observe(chartContainer);
    }
    updateSize();
    return () => observer.disconnect();
  }, [props]);

  return (
    <div
      ref={ref}
      className={`haeoThemeRoot ${props.showChartBounds === true ? "showChartBounds" : ""}`}
      style={{
        width: "100%",
        maxWidth: "1200px",
        height: props.height ?? "calc(100vh - 56px)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <ForecastCardView
        store={props.store}
        onPointerMove={(event) => {
          const svg = event.currentTarget as SVGSVGElement | null;
          if (!svg) {
            return;
          }
          const screenCtm = svg.getScreenCTM();
          if (!screenCtm) {
            throw new Error("Expected non-null SVG screen CTM for pointer mapping");
          }
          const inverse = screenCtm.inverse();
          const x = event.clientX * inverse.a + event.clientY * inverse.c + inverse.e;
          const y = event.clientX * inverse.b + event.clientY * inverse.d + inverse.f;
          props.store.setPointer(x, y);
        }}
        onPointerLeave={() => {
          props.store.setPointer(null, null);
        }}
      />
    </div>
  );
}
