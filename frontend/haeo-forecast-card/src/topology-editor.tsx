import { render } from "preact";
import { useCallback, useEffect, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";

import { t } from "./i18n";
import { isTopologyData } from "./topology-card-utils";
import type { TopologyCardConfig } from "./types";

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
  config: TopologyCardConfig;
  hass: HassEditorLike | null;
  onConfigChanged: (config: TopologyCardConfig) => void;
}

function discoverTopologyEntityForHub(
  hass: HassEditorLike,
  registry: EntityRegistryEntry[],
  hubEntryId: string
): string | null {
  let fallback: string | null = null;
  for (const entry of registry) {
    if (entry.platform !== "haeo" || entry.disabled_by !== null || entry.config_entry_id !== hubEntryId) {
      continue;
    }
    const state = hass.states[entry.entity_id];
    const topology = state?.attributes?.["topology"];
    if (!isTopologyData(topology)) {
      continue;
    }
    const outputName = state?.attributes?.["output_name"];
    if (outputName === "network_optimization_status") {
      return entry.entity_id;
    }
    fallback ??= entry.entity_id;
  }
  return fallback;
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
  const [resolvedEntity, setResolvedEntity] = useState<string | null>(config.entity ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const configRef = useRef(config);
  const onConfigChangedRef = useRef(onConfigChanged);
  configRef.current = config;
  onConfigChangedRef.current = onConfigChanged;

  const locale = hass?.language ?? hass?.locale?.language ?? "en";

  const refreshEntity = useCallback(
    (hubEntryId: string) => {
      if (!hass?.callWS) {
        setResolvedEntity(null);
        setError(t(locale, "topology.editor.error.ws_unavailable"));
        return;
      }
      setLoading(true);
      setError(null);
      void hass
        .callWS<EntityRegistryEntry[]>({ type: "config/entity_registry/list" })
        .then((registry) => {
          const entityId = discoverTopologyEntityForHub(hass, registry, hubEntryId);
          setResolvedEntity(entityId);
          const next: TopologyCardConfig = {
            ...configRef.current,
            type: "custom:haeo-topology-card",
            hub_entry_id: hubEntryId,
          };
          if (entityId !== null) {
            next.entity = entityId;
          } else {
            delete next.entity;
          }
          onConfigChangedRef.current(next);
        })
        .catch((err: unknown) => {
          setResolvedEntity(null);
          setError(err instanceof Error ? err.message : String(err));
        })
        .finally(() => setLoading(false));
    },
    [hass, locale]
  );

  useEffect(() => {
    if (config.hub_entry_id !== undefined && config.hub_entry_id !== "") {
      refreshEntity(config.hub_entry_id);
    }
  }, [config.hub_entry_id, refreshEntity]);

  const onHubChange = (hubEntryId: string): void => {
    if (!hubEntryId) {
      const next: TopologyCardConfig = {
        ...config,
        type: "custom:haeo-topology-card",
      };
      delete next.hub_entry_id;
      delete next.entity;
      setResolvedEntity(null);
      onConfigChanged(next);
      return;
    }
    refreshEntity(hubEntryId);
  };

  const onTitleChange = (event: Event): void => {
    const target = event.target as HTMLInputElement;
    const trimmed = target.value.trim();
    const next: TopologyCardConfig = {
      ...config,
      type: "custom:haeo-topology-card",
    };
    if (trimmed) {
      next.title = trimmed;
    } else {
      delete next.title;
    }
    onConfigChanged(next);
  };

  return (
    <div className="wrap">
      <label>
        {t(locale, "topology.editor.title.label")}
        <input
          type="text"
          value={config.title ?? ""}
          placeholder={t(locale, "topology.editor.title.placeholder")}
          onChange={onTitleChange}
        />
      </label>
      <label>
        {t(locale, "topology.editor.hub.label")}
        <HaSelectorBridge hass={hass} value={config.hub_entry_id ?? ""} onValueChanged={onHubChange} />
      </label>
      <div className="meta">
        {loading
          ? t(locale, "topology.editor.resolution.loading")
          : resolvedEntity !== null
            ? t(locale, "topology.editor.resolution.found", { entity: resolvedEntity })
            : config.hub_entry_id !== undefined && config.hub_entry_id !== ""
              ? t(locale, "topology.editor.resolution.none")
              : t(locale, "topology.editor.hub.placeholder")}
      </div>
      {error !== null && <div className="error">{error}</div>}
    </div>
  );
}

export class HaeoTopologyCardEditor extends HTMLElement {
  private _config: TopologyCardConfig = { type: "custom:haeo-topology-card" };
  private _hass: HassEditorLike | null = null;
  private _styleInstalled = false;

  setConfig(config: TopologyCardConfig): void {
    this._config = { ...config, type: "custom:haeo-topology-card" };
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

if (!customElements.get("haeo-topology-card-editor")) {
  customElements.define("haeo-topology-card-editor", HaeoTopologyCardEditor);
}
