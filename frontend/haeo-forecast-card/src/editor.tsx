import { render } from "preact";
import { useCallback, useEffect, useRef, useState } from "preact/hooks";
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

interface HubEntities {
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
  input {
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

function discoverEntitiesForHub(
  hass: HassEditorLike,
  registry: EntityRegistryEntry[],
  hubEntryId: string
): HubEntities {
  const entities: string[] = [];
  const names = new Set<string>();
  for (const entry of registry) {
    if (entry.platform !== "haeo" || entry.disabled_by !== null || entry.config_entry_id !== hubEntryId) {
      continue;
    }
    const state = hass.states[entry.entity_id];
    const forecast = state?.attributes?.["forecast"];
    if (!Array.isArray(forecast) || forecast.length === 0) {
      continue;
    }
    entities.push(entry.entity_id);
    const elementName = state?.attributes?.["element_name"];
    if (typeof elementName === "string" && elementName.trim().length > 0) {
      names.add(elementName);
    }
  }
  return {
    entities: entities.sort((a, b) => a.localeCompare(b)),
    elementNames: [...names].sort((a, b) => a.localeCompare(b)),
  };
}

function HaSelectorBridge(props: {
  hass: HassEditorLike | null;
  value: string;
  onValueChanged: (value: string) => void;
}): JSX.Element {
  const ref = useRef<HTMLElement | null>(null);
  const onValueChangedRef = useRef(props.onValueChanged);
  onValueChangedRef.current = props.onValueChanged;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handler = (ev: Event): void => {
      const detail = (ev as CustomEvent<{ value?: string }>).detail;
      const value = detail.value ?? "";
      onValueChangedRef.current(value);
    };
    el.addEventListener("value-changed", handler);
    return () => el.removeEventListener("value-changed", handler);
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const bridge = el as unknown as Record<string, unknown>;
    bridge["hass"] = props.hass;
    bridge["selector"] = { config_entry: { integration: "haeo" } };
    bridge["value"] = props.value;
  }, [props.hass, props.value]);

  return <ha-selector-config_entry ref={ref} />;
}

function EditorForm(props: EditorFormProps): JSX.Element {
  const { config, hass, onConfigChanged } = props;
  const [hubEntities, setHubEntities] = useState<HubEntities | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const configRef = useRef(config);
  const onConfigChangedRef = useRef(onConfigChanged);
  configRef.current = config;
  onConfigChangedRef.current = onConfigChanged;

  const locale = hass?.language ?? hass?.locale?.language ?? "en";

  const refreshEntities = useCallback(
    (hubEntryId: string) => {
      if (!hass?.callWS) return;
      setLoading(true);
      setError(null);
      void hass
        .callWS<EntityRegistryEntry[]>({ type: "config/entity_registry/list" })
        .then((registry) => {
          const result = discoverEntitiesForHub(hass, registry, hubEntryId);
          setHubEntities(result);
          onConfigChangedRef.current({
            ...configRef.current,
            type: "custom:haeo-forecast-card",
            hub_entry_id: hubEntryId,
            entities: result.entities,
          });
        })
        .catch((err: unknown) => {
          setHubEntities(null);
          setError(err instanceof Error ? err.message : String(err));
        })
        .finally(() => setLoading(false));
    },
    [hass]
  );

  useEffect(() => {
    if (config.hub_entry_id !== undefined && config.hub_entry_id !== "") {
      refreshEntities(config.hub_entry_id);
    }
  }, [config.hub_entry_id, refreshEntities]);

  const selectedEntityCount = hubEntities?.entities.length ?? config.entities?.length ?? 0;
  const selectedElementNames = hubEntities?.elementNames ?? [];

  const onHubChange = (hubEntryId: string): void => {
    if (!hubEntryId) return;
    refreshEntities(hubEntryId);
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
      <HaSelectorBridge hass={hass} value={config.hub_entry_id ?? ""} onValueChanged={onHubChange} />
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
