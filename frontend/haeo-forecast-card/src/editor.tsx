import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";

import { t } from "./i18n";
import type { ForecastCardConfig } from "./types";

interface EntityRegistryEntry {
  entity_id: string;
  platform: string;
  config_entry_id: string | null;
  disabled_by: string | null;
}

interface HassEditorLike {
  states: Record<string, { attributes?: Record<string, unknown> } | undefined>;
  callWS?: <T>(message: Record<string, unknown>) => Promise<T>;
  language?: string;
  locale?: { language?: string };
}

interface HubOption {
  entryId: string;
  entities: string[];
  elementNames: string[];
}

const EDITOR_STYLES = `
  :host {
    display: block;
    font-family: var(--paper-font-body1_-_font-family);
    color: var(--primary-text-color);
  }
  .wrap { display: grid; gap: 12px; }
  label { display: grid; gap: 6px; font-size: 13px; font-weight: 500; }
  select, input {
    font: inherit; color: inherit;
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px; padding: 8px 10px;
  }
  .meta { font-size: 12px; color: var(--secondary-text-color); line-height: 1.4; }
  .error { color: var(--error-color); font-size: 12px; }
`;

interface EditorFormProps {
  config: ForecastCardConfig;
  hass: HassEditorLike | null;
  onConfigChanged: (config: ForecastCardConfig) => void;
}

function discoverHubs(hass: HassEditorLike, registry: EntityRegistryEntry[]): HubOption[] {
  const byHub = new Map<string, string[]>();
  for (const entry of registry) {
    if (entry.platform !== "haeo" || entry.disabled_by !== null || entry.config_entry_id === null) {
      continue;
    }
    const state = hass.states[entry.entity_id];
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
      const attrs = hass.states[entityId]?.attributes ?? {};
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
  return options.sort((a, b) => a.entryId.localeCompare(b.entryId));
}

function EditorForm(props: EditorFormProps): JSX.Element {
  const { config, hass, onConfigChanged } = props;
  const [hubOptions, setHubOptions] = useState<HubOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoSelectedRef = useRef(false);
  const configRef = useRef(config);
  const onConfigChangedRef = useRef(onConfigChanged);
  configRef.current = config;
  onConfigChangedRef.current = onConfigChanged;

  const locale = hass?.language ?? hass?.locale?.language ?? "en";

  useEffect(() => {
    if (!hass?.callWS) {
      setHubOptions([]);
      setError(t(locale, "editor.error.ws_unavailable"));
      return;
    }
    setLoading(true);
    setError(null);
    const callWS = hass.callWS;
    void callWS<EntityRegistryEntry[]>({ type: "config/entity_registry/list" })
      .then((registry) => {
        const options = discoverHubs(hass, registry);
        setHubOptions(options);
        if (configRef.current.hub_entry_id === undefined && options.length > 0 && !autoSelectedRef.current) {
          const first = options[0];
          if (first) {
            autoSelectedRef.current = true;
            const option = options.find((o) => o.entryId === first.entryId);
            if (option) {
              onConfigChangedRef.current({
                ...configRef.current,
                type: "custom:haeo-forecast-card",
                hub_entry_id: first.entryId,
                entities: option.entities,
              });
            }
          }
        }
      })
      .catch((err: unknown) => {
        setHubOptions([]);
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [hass]);

  const selectedHub = config.hub_entry_id ?? "";
  const selectedOption = hubOptions.find((o) => o.entryId === selectedHub) ?? null;
  const selectedEntityCount = selectedOption?.entities.length ?? config.entities?.length ?? 0;
  const selectedElementNames = selectedOption?.elementNames ?? [];

  const onHubChange = (event: Event): void => {
    const target = event.target as HTMLSelectElement;
    const hubEntryId = target.value;
    const option = hubOptions.find((o) => o.entryId === hubEntryId);
    if (!option) {
      return;
    }
    onConfigChanged({
      ...config,
      type: "custom:haeo-forecast-card",
      hub_entry_id: hubEntryId,
      entities: option.entities,
    });
  };

  const onTitleChange = (event: Event): void => {
    const target = event.target as HTMLInputElement;
    const trimmed = target.value.trim();
    const next: ForecastCardConfig = {
      ...config,
      type: "custom:haeo-forecast-card",
    };
    if (trimmed) {
      next.title = trimmed;
    } else {
      delete next.title;
    }
    onConfigChanged(next);
  };

  const onHeightChange = (event: Event): void => {
    const target = event.target as HTMLInputElement;
    const parsed = Number(target.value);
    const next: ForecastCardConfig = {
      ...config,
      type: "custom:haeo-forecast-card",
    };
    if (Number.isFinite(parsed) && parsed >= 220) {
      next.height = parsed;
    } else {
      delete next.height;
    }
    onConfigChanged(next);
  };

  return (
    <div className="wrap">
      <label>
        {t(locale, "editor.title.label")}
        <input
          id="titleInput"
          type="text"
          value={config.title ?? ""}
          placeholder={t(locale, "editor.title.placeholder")}
          onChange={onTitleChange}
        />
      </label>
      <label>
        {t(locale, "editor.hub.label")}
        <select id="hubSelect" disabled={hubOptions.length === 0} onChange={onHubChange} value={selectedHub}>
          {hubOptions.length === 0 ? (
            <option value="">{t(locale, "editor.hub.none")}</option>
          ) : (
            hubOptions.map((option) => (
              <option key={option.entryId} value={option.entryId}>
                {option.entryId}
              </option>
            ))
          )}
        </select>
      </label>
      <div className="meta">
        {loading
          ? t(locale, "editor.discovery.loading")
          : t(locale, "editor.discovery.count", { count: selectedEntityCount })}
      </div>
      {selectedElementNames.length > 0 && (
        <div className="meta">{t(locale, "editor.elements.label", { elements: selectedElementNames.join(", ") })}</div>
      )}
      <label>
        {t(locale, "editor.height.label")}
        <input
          id="heightInput"
          type="number"
          min={220}
          step={10}
          value={config.height ?? ""}
          placeholder={t(locale, "editor.height.placeholder")}
          onChange={onHeightChange}
        />
      </label>
      {error !== null && <div className="error">{error}</div>}
    </div>
  );
}

export class HaeoForecastCardEditor extends HTMLElement {
  private _config: ForecastCardConfig = { type: "custom:haeo-forecast-card" };
  private _hass: HassEditorLike | null = null;
  private _styleInstalled = false;

  setConfig(config: ForecastCardConfig): void {
    this._config = { ...config };
    this.renderEditor();
  }

  set hass(hass: HassEditorLike) {
    this._hass = hass;
    this.renderEditor();
  }

  connectedCallback(): void {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this.renderEditor();
  }

  disconnectedCallback(): void {
    if (this.shadowRoot) {
      render(null, this.shadowRoot);
    }
  }

  private renderEditor(): void {
    if (!this.shadowRoot) {
      return;
    }
    if (!this._styleInstalled) {
      const style = document.createElement("style");
      style.textContent = EDITOR_STYLES;
      this.shadowRoot.appendChild(style);
      this._styleInstalled = true;
    }
    render(
      <EditorForm
        config={this._config}
        hass={this._hass}
        onConfigChanged={(next) => {
          this._config = next;
          this.dispatchEvent(
            new CustomEvent("config-changed", {
              detail: { config: next },
              bubbles: true,
              composed: true,
            })
          );
        }}
      />,
      this.shadowRoot
    );
  }
}

if (!customElements.get("haeo-forecast-card-editor")) {
  customElements.define("haeo-forecast-card-editor", HaeoForecastCardEditor);
}
