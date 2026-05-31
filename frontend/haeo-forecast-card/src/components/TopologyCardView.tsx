import type { JSX } from "preact";
import { useCallback, useEffect, useRef, useState } from "preact/hooks";

import { t } from "../i18n";
import type { HassLike } from "../series";
import { NetworkTopology } from "../topology/NetworkTopology";
import { readTopology, resolveTopologyEntity } from "../topology-card-utils";
import type { TopologyCardConfig } from "../types";

interface TopologyCardViewProps {
  config: TopologyCardConfig;
  hass: HassLike | null;
  locale: string | null | undefined;
  onLayoutHeight: (height: number) => void;
}

export function TopologyCardView(props: TopologyCardViewProps): JSX.Element {
  const { config, hass, locale, onLayoutHeight } = props;
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const [viewportWidth, setViewportWidth] = useState(640);
  const entityId = resolveTopologyEntity(config, hass);
  const topology = readTopology(hass, entityId);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (viewport === null) {
      return;
    }
    const updateWidth = (): void => {
      const width = viewport.getBoundingClientRect().width;
      if (width > 0) {
        setViewportWidth(width);
      }
    };
    updateWidth();
    const observer = new ResizeObserver(() => {
      updateWidth();
    });
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  const title = config.title ?? t(locale, "topology.card.title.default");
  const handleLayoutSize = useCallback(
    (_width: number, height: number) => {
      onLayoutHeight(height + 48);
    },
    [onLayoutHeight]
  );

  if (config.hub_entry_id === undefined || config.hub_entry_id === "") {
    return (
      <div className="topologyCard">
        <div className="topologyHeader">{title}</div>
        <div className="topologyMessage">{t(locale, "topology.card.empty.configure_hub")}</div>
      </div>
    );
  }

  if (entityId === null) {
    return (
      <div className="topologyCard">
        <div className="topologyHeader">{title}</div>
        <div className="topologyMessage">{t(locale, "topology.card.empty.no_entity")}</div>
      </div>
    );
  }

  if (topology === null) {
    return (
      <div className="topologyCard">
        <div className="topologyHeader">{title}</div>
        <div className="topologyMessage">{t(locale, "topology.card.empty.waiting", { entity: entityId })}</div>
      </div>
    );
  }

  return (
    <div className="topologyCard">
      <div className="topologyHeader">{title}</div>
      <div className="topologyViewport" ref={viewportRef}>
        <NetworkTopology
          topology={topology}
          width={viewportWidth}
          onLayoutSize={handleLayoutSize}
          layoutErrorMessage={t(locale, "topology.card.error.layout")}
          layoutLoadingMessage={t(locale, "topology.card.loading")}
        />
      </div>
    </div>
  );
}
