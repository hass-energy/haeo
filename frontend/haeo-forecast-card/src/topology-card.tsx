import { buildHubConfigForm } from "./config-form";
import { discoverHaeoHubEntryId } from "./hub-selection";
import type { HassLike } from "./series";
import type { TopologyCardController } from "./topology-card-controller";
import { topologyCardSize, TOPOLOGY_DEFAULT_LAYOUT_HEIGHT_PX } from "./topology-layout";
import type { TopologyCardConfig } from "./types";

const FALLBACK_CARD_SIZE_ROWS = topologyCardSize(TOPOLOGY_DEFAULT_LAYOUT_HEIGHT_PX);

function buildTopologyStubConfig(hass: HassLike): Omit<TopologyCardConfig, "type"> {
  const stub: Omit<TopologyCardConfig, "type"> = { title: "HAEO network topology" };
  const hubEntryId = discoverHaeoHubEntryId(hass);
  if (hubEntryId !== null) {
    stub.hub_entry_id = hubEntryId;
  }
  return stub;
}

/**
 * Thin custom element for `haeo-topology-card`.
 *
 * Kept free of heavy imports (preact, ELK, the SVG view) so that
 * `customElements.define` runs immediately when the bundle loads, avoiding the
 * Home Assistant "Custom element doesn't exist" registration race. The heavy
 * rendering controller is imported lazily on first use.
 */
export class HaeoTopologyCard extends HTMLElement {
  private controller: TopologyCardController | null = null;
  private controllerPromise: Promise<TopologyCardController> | null = null;
  private _config: TopologyCardConfig = { type: "custom:haeo-topology-card" };
  private _hass: HassLike | null = null;
  private isConnected_ = false;

  setConfig(config: TopologyCardConfig): void {
    this._config = { ...config, type: "custom:haeo-topology-card" };
    if (this.controller) {
      this.controller.setConfig(this._config);
    } else {
      void this.ensureController();
    }
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
    if (this.controller) {
      this.controller.setHass(hass);
    } else {
      void this.ensureController();
    }
  }

  get hass(): HassLike | null {
    return this._hass;
  }

  connectedCallback(): void {
    this.isConnected_ = true;
    if (this.controller) {
      this.controller.connected();
      return;
    }
    void this.ensureController();
  }

  disconnectedCallback(): void {
    this.isConnected_ = false;
    this.controller?.disconnected();
  }

  getCardSize(): number {
    return this.controller?.getCardSize() ?? FALLBACK_CARD_SIZE_ROWS;
  }

  getGridOptions(): {
    rows: number;
    min_rows: number;
    columns: "full";
  } {
    if (this.controller) {
      return this.controller.getGridOptions();
    }
    return {
      rows: FALLBACK_CARD_SIZE_ROWS,
      min_rows: Math.max(3, FALLBACK_CARD_SIZE_ROWS - 1),
      columns: "full",
    };
  }

  private async ensureController(): Promise<TopologyCardController> {
    this.controllerPromise ??= import("./topology-card-controller").then(({ TopologyCardController }) => {
      const controller = new TopologyCardController(this);
      this.controller = controller;
      controller.setConfig(this._config);
      if (this._hass) {
        controller.setHass(this._hass);
      }
      if (this.isConnected_) {
        controller.connected();
      }
      return controller;
    });
    return this.controllerPromise;
  }
}

if (!customElements.get("haeo-topology-card")) {
  customElements.define("haeo-topology-card", HaeoTopologyCard);
}
