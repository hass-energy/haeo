import type { JSX } from "preact";
import { useLayoutEffect, useRef } from "preact/hooks";

import { ForecastCardView } from "./ForecastCardView";
import type { ForecastCardStore } from "../store";

interface ResponsiveStoryFrameProps {
  store: ForecastCardStore;
  initialPointer?: { x: number; y: number };
}

export function ResponsiveStoryFrame(props: ResponsiveStoryFrameProps): JSX.Element {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) {
        return;
      }
      props.store.setSize(rect.width, props.store.responsiveHeight(rect.width));
      if (props.initialPointer) {
        props.store.setPointer(props.initialPointer.x, props.initialPointer.y);
      }
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [props]);

  return (
    <div ref={ref} className="haeoThemeRoot" style={{ width: "100%", maxWidth: "1200px", minHeight: "520px" }}>
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
