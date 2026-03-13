import { render } from "preact";

import { ForecastCardView } from "./components/ForecastCardView";
import type { HassLike } from "./series";
import { ForecastCardStore } from "./store";
import { CARD_STYLES } from "./styles";
import type { ForecastCardConfig } from "./types";

export class HaeoForecastCard extends HTMLElement {
  private readonly store = new ForecastCardStore();
  private resizeObserver: ResizeObserver | null = null;
  private frameHandle = 0;
  private hasRenderedHost = false;
  private _hass: HassLike | null = null;

  setConfig(config: ForecastCardConfig): void {
    this.store.setConfig(config);
    this.renderCard();
  }

  set hass(hass: HassLike | null) {
    this._hass = hass;
    if (hass) {
      this.store.setHass(hass);
    }
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
    this.startAnimationLoop();
    this.observeCardResize();
    this.renderCard();
  }

  disconnectedCallback(): void {
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    cancelAnimationFrame(this.frameHandle);
    if (this.shadowRoot) {
      render(null, this.shadowRoot);
    }
    this.hasRenderedHost = false;
  }

  getCardSize(): number {
    return 4;
  }

  private ensureHostElements(): void {
    if (!this.shadowRoot || this.hasRenderedHost) {
      return;
    }
    const style = document.createElement("style");
    style.textContent = CARD_STYLES;
    this.shadowRoot.appendChild(style);

    const mount = document.createElement("div");
    mount.id = "mount";
    this.shadowRoot.appendChild(mount);
    this.hasRenderedHost = true;
  }

  private observeCardResize(): void {
    if (!this.shadowRoot || !("ResizeObserver" in window)) {
      return;
    }
    const mount = this.shadowRoot.querySelector("#mount");
    if (!mount) {
      return;
    }
    this.resizeObserver?.disconnect();
    this.resizeObserver = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) {
        return;
      }
      this.store.setSize(rect.width, this.store.responsiveHeight(rect.width));
      this.renderCard();
    });
    this.resizeObserver.observe(mount);
  }

  private startAnimationLoop(): void {
    const tick = () => {
      this.store.setNow(Date.now());
      this.renderCard();
      if (this.store.motionMode === "smooth") {
        this.frameHandle = requestAnimationFrame(tick);
      }
    };
    this.frameHandle = requestAnimationFrame(tick);
  }

  private onPointerMove(event: PointerEvent): void {
    const svgElement = event.currentTarget as SVGElement | null;
    if (!svgElement) {
      return;
    }
    const rect = svgElement.getBoundingClientRect();
    this.store.setPointer(event.clientX - rect.left, event.clientY - rect.top);
    this.renderCard();
  }

  private onPointerLeave(): void {
    this.store.setPointer(null, null);
    this.renderCard();
  }

  private renderCard(): void {
    if (!this.shadowRoot) {
      return;
    }
    const mount = this.shadowRoot.querySelector("#mount");
    if (!mount) {
      return;
    }
    render(
      <ForecastCardView
        store={this.store}
        onPointerMove={(event) => this.onPointerMove(event)}
        onPointerLeave={() => this.onPointerLeave()}
      />,
      mount
    );
  }
}

if (!customElements.get("haeo-forecast-card")) {
  customElements.define("haeo-forecast-card", HaeoForecastCard);
}
