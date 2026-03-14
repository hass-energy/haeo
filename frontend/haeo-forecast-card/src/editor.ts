import type { ForecastCardConfig } from "./types";
import { t } from "./i18n";

type EntityRegistryEntry = {
  entity_id: string;
  platform: string;
  config_entry_id: string | null;
  disabled_by: string | null;
};

type HassEditorLike = {
  states: Record<string, { attributes?: Record<string, unknown> } | undefined>;
  callWS?: <T>(message: Record<string, unknown>) => Promise<T>;
  language?: string;
  locale?: { language?: string };
};

type HubOption = {
  entryId: string;
  entities: string[];
  elementNames: string[];
};

export class HaeoForecastCardEditor extends HTMLElement {
  private _config: ForecastCardConfig = { type: "custom:haeo-forecast-card" };
  private _hass: HassEditorLike | null = null;
  private hubOptions: HubOption[] = [];
  private loading = false;
  private error: string | null = null;

  private get locale(): string {
    return this._hass?.language ?? this._hass?.locale?.language ?? navigator.language ?? "en";
  }

  setConfig(config: ForecastCardConfig): void {
    this._config = { ...config };
    this.render();
  }

  set hass(hass: HassEditorLike) {
    this._hass = hass;
    void this.refreshDiscovery();
  }

  connectedCallback(): void {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    void this.refreshDiscovery();
    this.render();
  }

  private async refreshDiscovery(): Promise<void> {
    if (!this._hass?.callWS) {
      this.hubOptions = [];
      this.error = t(this.locale, "editor.error.ws_unavailable");
      this.render();
      return;
    }
    this.loading = true;
    this.error = null;
    this.render();
    try {
      const registry = await this._hass.callWS<EntityRegistryEntry[]>({
        type: "config/entity_registry/list",
      });
      const byHub = new Map<string, string[]>();
      for (const entry of registry) {
        if (entry.platform !== "haeo" || entry.disabled_by !== null || !entry.config_entry_id) {
          continue;
        }
        const state = this._hass.states[entry.entity_id];
        const forecast = state?.attributes?.["forecast"];
        if (!Array.isArray(forecast) || forecast.length === 0) {
          continue;
        }
        const list = byHub.get(entry.config_entry_id) ?? [];
        list.push(entry.entity_id);
        byHub.set(entry.config_entry_id, list);
      }
      const options: HubOption[] = [];
      for (const [entryId, entityIds] of byHub.entries()) {
        const names = new Set<string>();
        for (const entityId of entityIds) {
          const attrs = this._hass.states[entityId]?.attributes ?? {};
          const elementName = attrs["element_name"];
          if (typeof elementName === "string" && elementName.trim().length > 0) {
            names.add(elementName);
          }
        }
        options.push({
          entryId,
          entities: entityIds.sort((a, b) => a.localeCompare(b)),
          elementNames: [...names].sort((a, b) => a.localeCompare(b)),
        });
      }
      options.sort((a, b) => a.entryId.localeCompare(b.entryId));
      this.hubOptions = options;
      if (!this._config.hub_entry_id && options.length > 0) {
        const first = options[0];
        if (first) {
          this.updateConfigForHub(first.entryId);
          return;
        }
      }
      this.render();
    } catch (error) {
      this.hubOptions = [];
      this.error = error instanceof Error ? error.message : String(error);
      this.render();
    } finally {
      this.loading = false;
      this.render();
    }
  }

  private updateConfigForHub(hubEntryId: string): void {
    const option = this.hubOptions.find((candidate) => candidate.entryId === hubEntryId);
    if (!option) {
      return;
    }
    const nextConfig: ForecastCardConfig = {
      ...this._config,
      type: "custom:haeo-forecast-card",
      hub_entry_id: hubEntryId,
      entities: option.entities,
    };
    this._config = nextConfig;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: nextConfig },
        bubbles: true,
        composed: true,
      })
    );
    this.render();
  }

  private render(): void {
    if (!this.shadowRoot) {
      return;
    }
    const selectedHub = this._config.hub_entry_id ?? "";
    const selectedOption = this.hubOptions.find((option) => option.entryId === selectedHub) ?? null;
    const selectedEntityCount = selectedOption?.entities.length ?? this._config.entities?.length ?? 0;
    const selectedElementNames = selectedOption?.elementNames ?? [];
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: var(--paper-font-body1_-_font-family);
          color: var(--primary-text-color);
        }
        .wrap {
          display: grid;
          gap: 12px;
        }
        label {
          display: grid;
          gap: 6px;
          font-size: 13px;
          font-weight: 500;
        }
        select, input {
          font: inherit;
          color: inherit;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          padding: 8px 10px;
        }
        .meta {
          font-size: 12px;
          color: var(--secondary-text-color);
          line-height: 1.4;
        }
        .error {
          color: var(--error-color);
          font-size: 12px;
        }
      </style>
      <div class="wrap">
        <label>
          ${t(this.locale, "editor.title.label")}
          <input id="titleInput" type="text" value="${this._config.title ?? ""}" placeholder="${t(this.locale, "editor.title.placeholder")}" />
        </label>
        <label>
          ${t(this.locale, "editor.hub.label")}
          <select id="hubSelect" ${this.hubOptions.length === 0 ? "disabled" : ""}>
            ${
              this.hubOptions.length === 0
                ? `<option value="">${t(this.locale, "editor.hub.none")}</option>`
                : this.hubOptions
                    .map((option) => {
                      const selected = option.entryId === selectedHub ? "selected" : "";
                      return `<option value="${option.entryId}" ${selected}>${option.entryId}</option>`;
                    })
                    .join("")
            }
          </select>
        </label>
        <div class="meta">
          ${
            this.loading
              ? t(this.locale, "editor.discovery.loading")
              : t(this.locale, "editor.discovery.count", { count: selectedEntityCount })
          }
        </div>
        ${
          selectedElementNames.length > 0
            ? `<div class="meta">${t(this.locale, "editor.elements.label", { elements: selectedElementNames.join(", ") })}</div>`
            : ""
        }
        <label>
          ${t(this.locale, "editor.height.label")}
          <input id="heightInput" type="number" min="220" step="10" value="${this._config.height ?? ""}" placeholder="${t(this.locale, "editor.height.placeholder")}" />
        </label>
        ${this.error ? `<div class="error">${this.error}</div>` : ""}
      </div>
    `;

    const hubSelect = this.shadowRoot.querySelector<HTMLSelectElement>("#hubSelect");
    hubSelect?.addEventListener("change", (event) => {
      const target = event.target as HTMLSelectElement;
      this.updateConfigForHub(target.value);
    });

    const titleInput = this.shadowRoot.querySelector<HTMLInputElement>("#titleInput");
    titleInput?.addEventListener("change", (event) => {
      const target = event.target as HTMLInputElement;
      const trimmed = target.value.trim();
      const nextConfig: ForecastCardConfig = {
        ...this._config,
        type: "custom:haeo-forecast-card",
        ...(trimmed ? { title: trimmed } : {}),
      };
      if (!trimmed) {
        delete nextConfig.title;
      }
      this._config = nextConfig;
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config: nextConfig },
          bubbles: true,
          composed: true,
        })
      );
    });

    const heightInput = this.shadowRoot.querySelector<HTMLInputElement>("#heightInput");
    heightInput?.addEventListener("change", (event) => {
      const target = event.target as HTMLInputElement;
      const parsed = Number(target.value);
      const useHeight = Number.isFinite(parsed) && parsed >= 220;
      const nextConfig: ForecastCardConfig = {
        ...this._config,
        type: "custom:haeo-forecast-card",
        ...(useHeight ? { height: parsed } : {}),
      };
      if (!useHeight) {
        delete nextConfig.height;
      }
      this._config = nextConfig;
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config: nextConfig },
          bubbles: true,
          composed: true,
        })
      );
    });
  }
}

if (!customElements.get("haeo-forecast-card-editor")) {
  customElements.define("haeo-forecast-card-editor", HaeoForecastCardEditor);
}
