import { render } from "preact";
import { useMemo } from "preact/hooks";
import type { JSX } from "preact";

import { t } from "./i18n";
import { discoverTopologyEntities } from "./topology-card-utils";
import type { HassLike } from "./series";
import type { TopologyCardConfig } from "./types";

interface HassEditorLike {
  states: Record<string, { attributes?: Record<string, unknown> } | undefined>;
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
  input, select {
    font: inherit; color: inherit;
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 8px; padding: 8px 10px;
  }
  .meta { font-size: 12px; color: var(--secondary-text-color); line-height: 1.4; }
`;

interface EditorFormProps {
  config: TopologyCardConfig;
  hass: HassEditorLike | null;
  onConfigChanged: (config: TopologyCardConfig) => void;
}

function EditorForm(props: EditorFormProps): JSX.Element {
  const { config, hass, onConfigChanged } = props;
  const locale = hass?.language ?? hass?.locale?.language ?? "en";
  const discoveredEntities = useMemo(() => (hass ? discoverTopologyEntities(hass as HassLike) : []), [hass]);

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

  const onEntityChange = (event: Event): void => {
    const target = event.target as HTMLSelectElement;
    const next: TopologyCardConfig = {
      ...config,
      type: "custom:haeo-topology-card",
    };
    if (target.value) {
      next.entity = target.value;
    } else {
      delete next.entity;
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
        {t(locale, "topology.editor.entity.label")}
        <select value={config.entity ?? ""} onChange={onEntityChange}>
          <option value="">{t(locale, "topology.editor.entity.auto")}</option>
          {discoveredEntities.map((entityId) => (
            <option key={entityId} value={entityId}>
              {entityId}
            </option>
          ))}
        </select>
      </label>
      <div className="meta">
        {discoveredEntities.length > 0
          ? t(locale, "topology.editor.discovery.count", { count: discoveredEntities.length })
          : t(locale, "topology.editor.discovery.none")}
      </div>
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
