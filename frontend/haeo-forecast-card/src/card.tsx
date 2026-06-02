import { buildHubConfigForm } from "./config-form";
import { discoverHaeoHubEntryId } from "./hub-selection";
import type { HassLike } from "./series";
import type { ForecastCardConfig } from "./types";
import type { ForecastCardController } from "./forecast-card-controller";

const FALLBACK_CARD_WIDTH_PX = 640;
const FALLBACK_CARD_SIZE_ROWS = 6;
const FALLBACK_GRID_ROWS = 5;

/**
 * Thin custom element for `haeo-forecast-card`.
 *
 * This class is intentionally tiny and free of heavy imports (no preact, MobX,
 * or SVG view code) so that `customElements.define` runs immediately when the
 * bundle loads. Home Assistant only guarantees a custom card via
 * `customElements.whenDefined` plus a short timeout, so gating registration
 * behind a large dependency graph causes the intermittent "Custom element
 * doesn't exist" race. The heavy rendering stack is loaded lazily on first use.
 */
export class HaeoForecastCard extends HTMLElement {
  private static nextInstanceId = 0;
  private readonly instanceId = HaeoForecastCard.nextInstanceId++;
  private controller: ForecastCardController | null = null;
  private controllerPromise: Promise<ForecastCardController> | null = null;
  private _config: ForecastCardConfig | null = null;
  private _hass: HassLike | null = null;
  private isConnected_ = false;

  setConfig(config: ForecastCardConfig): void {
    this._config = config;
    if (this.controller) {
      this.controller.setConfig(config);
    } else {
      void this.ensureController();
    }
  }

  static getConfigForm(): ReturnType<typeof buildHubConfigForm> {
    return buildHubConfigForm();
  }

  static getStubConfig(hass?: HassLike): Omit<ForecastCardConfig, "type"> {
    const stub: Omit<ForecastCardConfig, "type"> = { title: "HAEO forecast" };
    if (hass === undefined) {
      return stub;
    }
    const hubEntryId = discoverHaeoHubEntryId(hass);
    if (hubEntryId !== null) {
      stub.hub_entry_id = hubEntryId;
    }
    return stub;
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
    return (
      this.controller?.getGridOptions() ?? {
        rows: FALLBACK_GRID_ROWS,
        min_rows: FALLBACK_GRID_ROWS - 1,
        columns: "full",
      }
    );
  }

  getCardWidth(): number {
    if (this.controller) {
      return this.controller.getCardWidth();
    }
    const width = this.getBoundingClientRect().width;
    return width > 0 ? width : FALLBACK_CARD_WIDTH_PX;
  }

  /**
   * Load the heavy rendering controller on demand and replay any buffered
   * config/hass/connection state into it. Registration of the element never
   * depends on this completing.
   */
  private async ensureController(): Promise<ForecastCardController> {
    this.controllerPromise ??= import("./forecast-card-controller").then(({ ForecastCardController }) => {
      const controller = new ForecastCardController(this, this.instanceId);
      this.controller = controller;
      if (this._config) {
        controller.setConfig(this._config);
      }
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

if (!customElements.get("haeo-forecast-card")) {
  customElements.define("haeo-forecast-card", HaeoForecastCard);
}
