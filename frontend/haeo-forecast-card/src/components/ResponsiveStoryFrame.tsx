import type { JSX } from "preact";
import { useLayoutEffect, useRef, useState } from "preact/hooks";

import { ForecastCardView } from "./ForecastCardView";
import type { ForecastCardStore } from "../store";

interface ResponsiveStoryFrameProps {
  store: ForecastCardStore;
  initialPointer?: { x: number; y: number };
}

export function ResponsiveStoryFrame(props: ResponsiveStoryFrameProps): JSX.Element {
  const ref = useRef<HTMLDivElement>(null);
  const [, setVersion] = useState(0);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element || !("ResizeObserver" in window)) {
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
      setVersion((value) => value + 1);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [props]);

  return (
    <div ref={ref} style={{ width: "100%", maxWidth: "1200px", minHeight: "520px" }}>
      <ForecastCardView
        store={props.store}
        onPointerMove={(event) => {
          const svg = event.currentTarget as SVGElement | null;
          if (!svg) {
            return;
          }
          const rect = svg.getBoundingClientRect();
          props.store.setPointer(event.clientX - rect.left, event.clientY - rect.top);
          setVersion((value) => value + 1);
        }}
        onPointerLeave={() => {
          props.store.setPointer(null, null);
          setVersion((value) => value + 1);
        }}
      />
    </div>
  );
}
