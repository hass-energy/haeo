import { render } from "preact";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { ForecastCardView } from "./components/ForecastCardView";
import type { HassLike } from "./series";
import { ForecastCardStore } from "./store";
import { CARD_STYLES } from "./styles";
import type { ForecastCardConfig } from "./types";

export class HaeoForecastCard extends HTMLElement {
  private static readonly MASONRY_ROW_HEIGHT_PX = 50;
  private static readonly SECTIONS_ROW_HEIGHT_PX = 56;
  private static readonly SECTIONS_ROW_GAP_PX = 8;
  private static nextInstanceId = 0;
  readonly instanceId = HaeoForecastCard.nextInstanceId++;
  private readonly store = new ForecastCardStore(this.instanceId);
  private resizeObserver: ResizeObserver | null = null;
  private frameHandle = 0;
  private pointerFrameHandle = 0;
  private pointerFlushScheduled = false;
  private pendingPointer: { x: number | null; y: number | null } | null = null;
  private hasRenderedHost = false;
  private _hass: HassLike | null = null;
  private animationPaused = false;
  private intersectionObserver: IntersectionObserver | null = null;
  private isIntersecting = true;

  setConfig(config: ForecastCardConfig): void {
    this.store.setConfig(config);
  }

  static getConfigElement(): HTMLElement {
    return document.createElement("haeo-forecast-card-editor");
  }

  static getStubConfig(): Omit<ForecastCardConfig, "type"> {
    return {
      title: "HAEO forecast",
    };
  }

  set hass(hass: HassLike | null) {
    this._hass = hass;
    if (hass) {
      this.store.setHass(hass);
    }
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
    this.observeVisibility();
    this.renderCard();
  }

  disconnectedCallback(): void {
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    this.intersectionObserver?.disconnect();
    this.intersectionObserver = null;
    document.removeEventListener("visibilitychange", this.onVisibilityChange);
    cancelAnimationFrame(this.frameHandle);
    if (this.pointerFlushScheduled) {
      cancelAnimationFrame(this.pointerFrameHandle);
      this.pointerFlushScheduled = false;
      this.pendingPointer = null;
    }
    if (this.shadowRoot) {
      render(null, this.shadowRoot);
    }
    this.hasRenderedHost = false;
  }

  getCardSize(): number {
    const targetHeight = this.store.config.height ?? this.store.height;
    return Math.max(1, Math.ceil(targetHeight / HaeoForecastCard.MASONRY_ROW_HEIGHT_PX));
  }

  getGridOptions(): {
    rows: number;
    min_rows: number;
    max_rows?: number;
    columns: "full";
  } {
    const targetHeight = this.store.config.height ?? this.store.height;
    const rowUnit = HaeoForecastCard.SECTIONS_ROW_HEIGHT_PX + HaeoForecastCard.SECTIONS_ROW_GAP_PX;
    const rows = Math.max(2, Math.ceil((targetHeight + HaeoForecastCard.SECTIONS_ROW_GAP_PX) / rowUnit));
    if (this.store.config.height !== undefined) {
      return {
        rows,
        min_rows: rows,
        max_rows: rows,
        columns: "full",
      };
    }
    return {
      rows,
      min_rows: Math.max(2, rows - 1),
      columns: "full",
    };
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
    mount.style.width = "100%";
    this.shadowRoot.appendChild(mount);
    this.hasRenderedHost = true;
  }

  private observeCardResize(): void {
    if (!this.shadowRoot) {
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
      const width = rect.width > 0 ? rect.width : mount.getBoundingClientRect().width;
      if (width <= 0) {
        return;
      }
      this.store.setSize(width, this.store.responsiveHeight(width));
    });
    this.resizeObserver.observe(mount);
    const initialWidth = mount.getBoundingClientRect().width;
    if (initialWidth > 0) {
      this.store.setSize(initialWidth, this.store.responsiveHeight(initialWidth));
    }
  }

  private startAnimationLoop(): void {
    const tick = (): void => {
      if (this.animationPaused) {
        return;
      }
      const hovering = this.store.pointerX !== null && this.store.pointerY !== null;
      if (!hovering) {
        this.store.setNow(Date.now());
      }
      if (this.store.motionMode === "smooth") {
        this.frameHandle = requestAnimationFrame(tick);
      }
    };
    this.frameHandle = requestAnimationFrame(tick);
  }

  private observeVisibility(): void {
    document.addEventListener("visibilitychange", this.onVisibilityChange);
    this.intersectionObserver = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry) {
          this.isIntersecting = entry.isIntersecting;
          this.updateAnimationPaused();
        }
      },
      { threshold: 0 },
    );
    this.intersectionObserver.observe(this);
  }

  private readonly onVisibilityChange = (): void => {
    this.updateAnimationPaused();
  };

  private updateAnimationPaused(): void {
    const shouldPause = document.hidden || !this.isIntersecting;
    if (shouldPause === this.animationPaused) {
      return;
    }
    this.animationPaused = shouldPause;
    if (!shouldPause && this.store.motionMode === "smooth") {
      this.startAnimationLoop();
    }
  }

  private onPointerMove(event: PointerEvent): void {
    const svgElement = event.currentTarget as SVGSVGElement | null;
    if (!svgElement) {
      return;
    }
    const screenCtm = svgElement.getScreenCTM();
    if (!screenCtm) {
      throw new Error("Expected non-null SVG screen CTM for pointer mapping");
    }
    const inverse = screenCtm.inverse();
    const x = Math.round(event.clientX * inverse.a + event.clientY * inverse.c + inverse.e);
    const y = Math.round(event.clientX * inverse.b + event.clientY * inverse.d + inverse.f);
    this.schedulePointerUpdate(x, y);
  }

  private onPointerLeave(): void {
    this.schedulePointerUpdate(null, null);
  }

  private schedulePointerUpdate(x: number | null, y: number | null): void {
    this.pendingPointer = { x, y };
    if (this.pointerFlushScheduled) {
      return;
    }
    this.pointerFlushScheduled = true;
    this.pointerFrameHandle = requestAnimationFrame(() => {
      this.pointerFlushScheduled = false;
      const pending = this.pendingPointer;
      this.pendingPointer = null;
      if (!pending) {
        return;
      }
      if (pending.x === null || pending.y === null) {
        if (this.store.pointerX === null && this.store.pointerY === null) {
          return;
        }
        this.store.setPointer(null, null);
        return;
      }
      if (this.store.pointerX !== null && this.store.pointerY !== null) {
        const deltaX = Math.abs(this.store.pointerX - pending.x);
        const deltaY = Math.abs(this.store.pointerY - pending.y);
        if (deltaX < 1 && deltaY < 1) {
          return;
        }
      }
      if (this.store.pointerX === pending.x && this.store.pointerY === pending.y) {
        return;
      }
      this.store.setPointer(pending.x, pending.y);
    });
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
      <ErrorBoundary>
        <ForecastCardView
          store={this.store}
          onPointerMove={(event) => this.onPointerMove(event)}
          onPointerLeave={() => this.onPointerLeave()}
        />
      </ErrorBoundary>,
      mount
    );
  }
}

if (!customElements.get("haeo-forecast-card")) {
  customElements.define("haeo-forecast-card", HaeoForecastCard);
}
