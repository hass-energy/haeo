import { render } from "preact";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { ForecastCardView } from "./components/ForecastCardView";
import type { HassLike } from "./series";
import { ForecastCardStore } from "./store";
import CARD_STYLES from "./styles.css";
import type { ForecastCardConfig } from "./types";

const MASONRY_ROW_HEIGHT_PX = 50;
const SECTIONS_ROW_HEIGHT_PX = 56;
const SECTIONS_ROW_GAP_PX = 8;

/**
 * Owns the heavy rendering stack (preact, MobX store, SVG view) for the forecast
 * card. It is loaded lazily by the thin `haeo-forecast-card` element so that
 * custom-element registration never waits on this code to download or evaluate.
 */
export class ForecastCardController {
  private readonly store: ForecastCardStore;
  private resizeObserver: ResizeObserver | null = null;
  private pointerFrameHandle = 0;
  private pointerFlushScheduled = false;
  private pendingPointer: { x: number | null; y: number | null } | null = null;
  private hasRenderedHost = false;
  private lastReportedCardSize: number | null = null;

  constructor(
    private readonly host: HTMLElement,
    instanceId: number
  ) {
    this.store = new ForecastCardStore(instanceId);
  }

  setConfig(config: ForecastCardConfig): void {
    this.store.setConfig(config);
    this.renderCard();
  }

  setHass(hass: HassLike | null): void {
    if (hass) {
      this.store.setHass(hass);
    }
    this.renderCard();
  }

  connected(): void {
    if (!this.host.shadowRoot) {
      this.host.attachShadow({ mode: "open" });
    }
    this.ensureHostElements();
    this.renderCard();
    this.observeCardResize();
    this.notifyCardSizeChanged();
  }

  disconnected(): void {
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    if (this.pointerFlushScheduled) {
      cancelAnimationFrame(this.pointerFrameHandle);
      this.pointerFlushScheduled = false;
      this.pendingPointer = null;
    }
    if (this.host.shadowRoot) {
      render(null, this.host.shadowRoot);
    }
    this.hasRenderedHost = false;
  }

  getCardSize(): number {
    const targetHeight = this.store.responsiveHeight(this.store.cardWidth);
    return Math.max(1, Math.ceil(targetHeight / MASONRY_ROW_HEIGHT_PX));
  }

  getGridOptions(): {
    rows: number;
    min_rows: number;
    columns: "full";
  } {
    const targetHeight = this.store.responsiveHeight(this.store.cardWidth);
    const rowUnit = SECTIONS_ROW_HEIGHT_PX + SECTIONS_ROW_GAP_PX;
    const rows = Math.max(2, Math.ceil((targetHeight + SECTIONS_ROW_GAP_PX) / rowUnit));
    return {
      rows,
      min_rows: Math.max(2, rows - 1),
      columns: "full",
    };
  }

  getCardWidth(): number {
    const mount = this.host.shadowRoot?.querySelector("#mount");
    const width = mount?.getBoundingClientRect().width ?? this.host.getBoundingClientRect().width;
    return width > 0 ? width : this.store.cardWidth;
  }

  private ensureHostElements(): void {
    if (!this.host.shadowRoot || this.hasRenderedHost) {
      return;
    }
    const style = document.createElement("style");
    style.textContent = CARD_STYLES;
    this.host.shadowRoot.appendChild(style);

    const mount = document.createElement("div");
    mount.id = "mount";
    mount.style.cssText = "width: 100%; height: 100%; display: flex; flex-direction: column;";
    this.host.shadowRoot.appendChild(mount);
    this.hasRenderedHost = true;
  }

  private observeCardResize(): void {
    if (!this.host.shadowRoot) {
      return;
    }
    const target =
      this.host.shadowRoot.querySelector(".chartContainer") ?? this.host.shadowRoot.querySelector("#mount");
    if (!target) {
      return;
    }
    this.resizeObserver?.disconnect();
    this.resizeObserver = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) {
        return;
      }
      const width = rect.width > 0 ? rect.width : target.getBoundingClientRect().width;
      if (width <= 0) {
        return;
      }
      const cardWidth = this.getCardWidth();
      const height = rect.height > 0 ? rect.height : this.store.responsiveHeight(cardWidth);
      this.store.setSize(width, height, cardWidth);
      this.notifyCardSizeChanged();
    });
    this.resizeObserver.observe(target);
    const initialRect = target.getBoundingClientRect();
    if (initialRect.width > 0) {
      const cardWidth = this.getCardWidth();
      const height = initialRect.height > 0 ? initialRect.height : this.store.responsiveHeight(cardWidth);
      this.store.setSize(initialRect.width, height, cardWidth);
      this.notifyCardSizeChanged();
    }
  }

  /**
   * Tell Home Assistant to re-query `getCardSize()` once the lazily-loaded
   * layout produces a different size than was reported by the thin element's
   * fallback. Mirrors the topology card's `ll-update` behavior.
   */
  private notifyCardSizeChanged(): void {
    const cardSize = this.getCardSize();
    if (cardSize === this.lastReportedCardSize) {
      return;
    }
    this.lastReportedCardSize = cardSize;
    this.host.dispatchEvent(new Event("ll-update", { bubbles: true, composed: true }));
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
    if (!this.host.shadowRoot || !this.hasRenderedHost) {
      return;
    }
    const mount = this.host.shadowRoot.querySelector("#mount");
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
