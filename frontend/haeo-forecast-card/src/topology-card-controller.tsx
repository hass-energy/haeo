import { render } from "preact";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { TopologyCardView } from "./components/TopologyCardView";
import type { HassLike } from "./series";
import { topologyCardSize, TOPOLOGY_DEFAULT_LAYOUT_HEIGHT_PX } from "./topology-layout";
import TOPOLOGY_CARD_STYLES from "./topology-card.css";
import type { TopologyCardConfig } from "./types";

/**
 * Owns the heavy rendering stack (preact, ELK layout, SVG view) for the
 * topology card. Loaded lazily by the thin `haeo-topology-card` element so that
 * custom-element registration never waits on ELK to download or evaluate.
 */
export class TopologyCardController {
  private _config: TopologyCardConfig = { type: "custom:haeo-topology-card" };
  private _hass: HassLike | null = null;
  private _layoutHeight = TOPOLOGY_DEFAULT_LAYOUT_HEIGHT_PX;

  constructor(private readonly host: HTMLElement) {}

  setConfig(config: TopologyCardConfig): void {
    this._config = { ...config, type: "custom:haeo-topology-card" };
    this.renderCard();
  }

  setHass(hass: HassLike | null): void {
    this._hass = hass;
    this.renderCard();
  }

  connected(): void {
    if (!this.host.shadowRoot) {
      this.host.attachShadow({ mode: "open" });
    }
    this.ensureHostElements();
    this.renderCard();
  }

  disconnected(): void {
    if (this.host.shadowRoot) {
      render(null, this.host.shadowRoot);
    }
  }

  getCardSize(): number {
    return topologyCardSize(this._layoutHeight);
  }

  getGridOptions(): {
    rows: number;
    min_rows: number;
    columns: "full";
  } {
    const rows = this.getCardSize();
    return {
      rows,
      min_rows: Math.max(3, rows - 1),
      columns: "full",
    };
  }

  private ensureHostElements(): void {
    if (!this.host.shadowRoot || this.host.shadowRoot.querySelector("#mount")) {
      return;
    }
    const style = document.createElement("style");
    style.textContent = TOPOLOGY_CARD_STYLES;
    this.host.shadowRoot.appendChild(style);

    const mount = document.createElement("div");
    mount.id = "mount";
    mount.style.cssText = "width: 100%; height: 100%; display: flex; flex-direction: column;";
    this.host.shadowRoot.appendChild(mount);
  }

  private readonly onLayoutHeight = (height: number): void => {
    const previousCardSize = this.getCardSize();
    this._layoutHeight = height;
    if (this.getCardSize() === previousCardSize) {
      return;
    }
    this.host.dispatchEvent(new Event("ll-update", { bubbles: true, composed: true }));
  };

  private renderCard(): void {
    if (this.host.shadowRoot === null) {
      return;
    }
    this.ensureHostElements();
    const mount = this.host.shadowRoot.querySelector("#mount");
    if (mount === null) {
      return;
    }
    const locale = this._hass?.language ?? this._hass?.locale?.language ?? "en";
    render(
      <ErrorBoundary>
        <TopologyCardView
          config={this._config}
          hass={this._hass}
          locale={locale}
          onLayoutHeight={this.onLayoutHeight}
        />
      </ErrorBoundary>,
      mount
    );
  }
}
