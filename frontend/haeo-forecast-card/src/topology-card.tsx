import { render } from "preact";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { TopologyCardView } from "./components/TopologyCardView";
import { buildHubConfigForm } from "./config-form";
import { discoverHaeoHubEntryId } from "./hub-selection";
import type { HassLike } from "./series";
import TOPOLOGY_CARD_STYLES from "./topology-card.css";
import { resolveTopologyEntity } from "./topology-card-utils";
import type { TopologyCardConfig } from "./types";

function buildTopologyStubConfig(hass: HassLike): Omit<TopologyCardConfig, "type"> {
  const stub: Omit<TopologyCardConfig, "type"> = { title: "HAEO network topology" };
  const hubEntryId = discoverHaeoHubEntryId(hass);
  if (hubEntryId !== null) {
    stub.hub_entry_id = hubEntryId;
  }
  const entity = resolveTopologyEntity({ type: "custom:haeo-topology-card", ...stub }, hass);
  if (entity !== null) {
    stub.entity = entity;
  }
  return stub;
}

export class HaeoTopologyCard extends HTMLElement {
  private static readonly MASONRY_ROW_HEIGHT_PX = 50;
  private _config: TopologyCardConfig = { type: "custom:haeo-topology-card" };
  private _hass: HassLike | null = null;
  private _layoutHeight = 320;

  setConfig(config: TopologyCardConfig): void {
    this._config = { ...config, type: "custom:haeo-topology-card" };
    this.renderCard();
  }

  static getConfigForm(): ReturnType<typeof buildHubConfigForm> {
    return buildHubConfigForm();
  }

  static getStubConfig(hass?: HassLike): Omit<TopologyCardConfig, "type"> {
    if (hass === undefined) {
      return { title: "HAEO network topology" };
    }
    return buildTopologyStubConfig(hass);
  }

  set hass(hass: HassLike | null) {
    this._hass = hass;
    this.renderCard();
  }

  get hass(): HassLike | null {
    return this._hass;
  }

  connectedCallback(): void {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this.ensureHostElements();
    this.renderCard();
  }

  disconnectedCallback(): void {
    if (this.shadowRoot) {
      render(null, this.shadowRoot);
    }
  }

  getCardSize(): number {
    return Math.max(4, Math.ceil(this._layoutHeight / HaeoTopologyCard.MASONRY_ROW_HEIGHT_PX));
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
    if (!this.shadowRoot || this.shadowRoot.querySelector("#mount")) {
      return;
    }
    const style = document.createElement("style");
    style.textContent = TOPOLOGY_CARD_STYLES;
    this.shadowRoot.appendChild(style);

    const mount = document.createElement("div");
    mount.id = "mount";
    mount.style.cssText = "width: 100%; height: 100%; display: flex; flex-direction: column;";
    this.shadowRoot.appendChild(mount);
  }

  private readonly onLayoutHeight = (height: number): void => {
    const previousCardSize = this.getCardSize();
    this._layoutHeight = height;
    if (this.getCardSize() === previousCardSize) {
      return;
    }
    this.dispatchEvent(new Event("ll-update", { bubbles: true, composed: true }));
  };

  private renderCard(): void {
    if (this.shadowRoot === null) {
      return;
    }
    this.ensureHostElements();
    const mount = this.shadowRoot.querySelector("#mount");
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

if (!customElements.get("haeo-topology-card")) {
  customElements.define("haeo-topology-card", HaeoTopologyCard);
}
