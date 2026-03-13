import { autorun } from "mobx";
import { LitElement, css, html, nothing, svg } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { linePath } from "./geometry";
import type { HassLike } from "./series";
import { ForecastCardStore } from "./store";
import type { ForecastCardConfig } from "./types";

function stepAreaPath(
  times: Float64Array,
  lower: Float64Array,
  upper: Float64Array,
  x: (time: number) => number,
  y: (value: number) => number
): string {
  if (times.length === 0) {
    return "";
  }
  const firstTime = times[0];
  const firstUpper = upper[0];
  if (firstTime === undefined || firstUpper === undefined) {
    return "";
  }
  let path = `M ${x(firstTime)} ${y(firstUpper)}`;
  for (let idx = 1; idx < times.length; idx += 1) {
    const currTime = times[idx];
    const prevUpper = upper[idx - 1];
    const currUpper = upper[idx];
    if (currTime === undefined || prevUpper === undefined || currUpper === undefined) {
      continue;
    }
    path += ` L ${x(currTime)} ${y(prevUpper)} L ${x(currTime)} ${y(currUpper)}`;
  }
  const lastTime = times[times.length - 1];
  const lastLower = lower[times.length - 1];
  if (lastTime === undefined || lastLower === undefined) {
    return "";
  }
  path += ` L ${x(lastTime)} ${y(lastLower)}`;
  for (let idx = times.length - 1; idx >= 1; idx -= 1) {
    const currTime = times[idx];
    const prevTime = times[idx - 1];
    const prevLower = lower[idx - 1];
    if (currTime === undefined || prevTime === undefined || prevLower === undefined) {
      continue;
    }
    path += ` L ${x(currTime)} ${y(prevLower)} L ${x(prevTime)} ${y(prevLower)}`;
  }
  return `${path} Z`;
}

@customElement("haeo-forecast-card")
export class HaeoForecastCard extends LitElement {
  static override styles = css`
    :host {
      display: block;
      position: relative;
      font-family: "Segoe UI", "Roboto", system-ui, sans-serif;
    }

    ha-card {
      overflow: hidden;
      position: relative;
      min-height: 220px;
    }

    .title {
      font-size: 1rem;
      font-weight: 600;
      padding: 16px 16px 0;
    }

    svg {
      width: 100%;
      display: block;
      touch-action: none;
    }

    .axisLabel {
      fill: var(--secondary-text-color);
      font-size: 11px;
      dominant-baseline: middle;
    }

    .laneDivider {
      stroke: color-mix(in oklab, var(--divider-color) 70%, transparent);
      stroke-width: 1;
    }

    .grid {
      stroke: color-mix(in oklab, var(--divider-color) 50%, transparent);
      stroke-width: 1;
      stroke-dasharray: 2 4;
    }

    .hoverLine {
      stroke: var(--primary-color);
      stroke-width: 1;
      stroke-dasharray: 4 4;
      pointer-events: none;
    }

    .lineSeries {
      fill: none;
      stroke-width: 2;
      pointer-events: none;
    }

    .areaSeries {
      stroke-width: 1;
      pointer-events: none;
    }

    .legend {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 6px 10px;
      padding: 0 16px 14px;
      font-size: 12px;
    }

    .legendItem {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      cursor: pointer;
      color: var(--primary-text-color);
      opacity: 0.72;
    }

    .legendItem.active {
      opacity: 1;
      font-weight: 600;
    }

    .legendSwatch {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      flex: 0 0 auto;
    }

    .legendText {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .tooltip {
      position: absolute;
      right: 14px;
      top: 14px;
      max-width: min(320px, calc(100% - 28px));
      background: color-mix(in oklab, var(--card-background-color) 86%, #000 14%);
      border: 1px solid color-mix(in oklab, var(--divider-color) 70%, transparent);
      border-radius: 10px;
      padding: 10px 11px;
      backdrop-filter: blur(6px);
      font-size: 12px;
      pointer-events: none;
    }

    .tooltipTime {
      font-weight: 600;
      margin-bottom: 6px;
    }

    .tooltipRow {
      display: grid;
      grid-template-columns: 10px 1fr auto;
      align-items: center;
      gap: 6px;
      line-height: 1.35;
      margin-bottom: 3px;
    }

    .tooltipDot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
    }

    .tooltipTotals {
      margin-top: 6px;
      padding-top: 6px;
      border-top: 1px solid color-mix(in oklab, var(--divider-color) 70%, transparent);
      display: grid;
      gap: 3px;
    }

    .empty {
      padding: 20px 16px 18px;
      color: var(--secondary-text-color);
      font-size: 0.9rem;
    }
  `;

  @property({ attribute: false }) hass: HassLike | null = null;
  @state() private store = new ForecastCardStore();

  private cleanupAutoRun: (() => void) | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private frameHandle = 0;

  setConfig(config: ForecastCardConfig): void {
    this.store.setConfig(config);
  }

  override connectedCallback(): void {
    super.connectedCallback();
    this.cleanupAutoRun = autorun(() => {
      void this.store.hasData;
      void this.store.tooltipRows;
      this.requestUpdate();
    });
    this.startAnimationLoop();
  }

  override firstUpdated(): void {
    const card = this.renderRoot.querySelector("ha-card");
    if (card && "ResizeObserver" in window) {
      this.resizeObserver = new ResizeObserver((entries) => {
        const rect = entries[0]?.contentRect;
        if (!rect) {
          return;
        }
        this.store.setSize(rect.width, this.store.chartHeight);
      });
      this.resizeObserver.observe(card);
    }
  }

  override disconnectedCallback(): void {
    this.cleanupAutoRun?.();
    this.cleanupAutoRun = null;
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    cancelAnimationFrame(this.frameHandle);
    super.disconnectedCallback();
  }

  protected override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("hass") && this.hass) {
      this.store.setHass(this.hass);
    }
  }

  getCardSize(): number {
    return 4;
  }

  private startAnimationLoop(): void {
    const tick = () => {
      this.store.setNow(Date.now());
      if (this.store.motionMode === "smooth") {
        this.frameHandle = requestAnimationFrame(tick);
      }
    };
    this.frameHandle = requestAnimationFrame(tick);
  }

  private onPointerMove(event: PointerEvent): void {
    const svgElement = event.currentTarget as SVGElement;
    const rect = svgElement.getBoundingClientRect();
    this.store.setPointer(event.clientX - rect.left, event.clientY - rect.top);
  }

  private onPointerLeave(): void {
    this.store.setPointer(null, null);
  }

  private renderLaneGraphics(): unknown[] {
    const graphics: unknown[] = [];
    const lanes = [...this.store.laneSeries.entries()];

    lanes.forEach(([lane, seriesList], laneIndex) => {
      const rect = this.store.laneRects.get(lane);
      if (!rect) {
        return;
      }
      if (laneIndex > 0) {
        graphics.push(
          svg`<line class="laneDivider" x1=${this.store.margins.left} y1=${rect.top} x2=${this.store.width - this.store.margins.right} y2=${rect.top}></line>`
        );
      }
      graphics.push(svg`<text class="axisLabel" x=${8} y=${(rect.top + rect.bottom) * 0.5}>${lane}</text>`);

      const stepSeries = seriesList.filter((series) => series.drawType === "step");
      const lineSeries = seriesList.filter((series) => series.drawType === "line");
      if (stepSeries.length > 0) {
        const firstStepSeries = stepSeries[0];
        if (!firstStepSeries) {
          return;
        }
        const horizonCount = firstStepSeries.times.length;
        const positive = new Float64Array(horizonCount);
        const negative = new Float64Array(horizonCount);
        for (const series of stepSeries) {
          const opacity = this.store.highlightedSeries && this.store.highlightedSeries !== series.key ? 0.22 : 0.66;
          const lower = new Float64Array(horizonCount);
          const upper = new Float64Array(horizonCount);
          for (let idx = 0; idx < horizonCount; idx += 1) {
            const value = series.values[idx] ?? 0;
            if (value >= 0) {
              lower[idx] = positive[idx] ?? 0;
              upper[idx] = (positive[idx] ?? 0) + value;
              positive[idx] = (positive[idx] ?? 0) + value;
            } else {
              lower[idx] = negative[idx] ?? 0;
              upper[idx] = (negative[idx] ?? 0) + value;
              negative[idx] = (negative[idx] ?? 0) + value;
            }
          }
          graphics.push(
            svg`<path
              class="areaSeries"
              fill=${series.color}
              stroke=${series.color}
              opacity=${opacity}
              d=${stepAreaPath(
                series.times,
                lower,
                upper,
                (time) => this.store.xScale(time),
                (value) => this.store.yScale(lane, value)
              )}
            ></path>`
          );
        }
      }

      for (const series of lineSeries) {
        const opacity = this.store.highlightedSeries && this.store.highlightedSeries !== series.key ? 0.25 : 0.78;
        const x = (time: number) => this.store.xScale(time);
        const y = (value: number) => this.store.yScale(lane, value);
        graphics.push(
          svg`<path
            class="lineSeries"
            stroke=${series.color}
            opacity=${opacity}
            d=${linePath(series.points, x, y)}
          ></path>`
        );
      }
    });

    return graphics;
  }

  private renderTooltip(): unknown {
    const rows = this.store.tooltipRows;
    const hoverTime = this.store.hoverTimeMs;
    if (rows.length === 0 || hoverTime === null) {
      return nothing;
    }
    const tooltipRows = rows.slice(0, 10);
    const totals = this.store.tooltipTotals;
    return html`
      <div class="tooltip">
        <div class="tooltipTime">${new Date(hoverTime).toLocaleString()}</div>
        ${tooltipRows.map(
          (row) => html`
            <div class="tooltipRow">
              <span class="tooltipDot" style="background:${row.color}"></span>
              <span>${row.label}</span>
              <span>${row.value.toFixed(2)} ${row.unit}</span>
            </div>
          `
        )}
        <div class="tooltipTotals">
          ${totals.map(
            (total) => html`<div><strong>${total.lane} total:</strong> ${total.value.toFixed(2)} ${total.unit}</div>`
          )}
        </div>
      </div>
    `;
  }

  private renderLegend(): unknown {
    return html`<div class="legend">
      ${this.store.normalizedSeries.map(
        (series) => html`
          <div
            class="legendItem ${this.store.highlightedSeries === series.key ? "active" : ""}"
            @mouseenter=${() => this.store.setHighlightedSeries(series.key)}
            @mouseleave=${() => this.store.setHighlightedSeries(null)}
          >
            <span class="legendSwatch" style="background:${series.color}"></span>
            <span class="legendText">${series.label}</span>
          </div>
        `
      )}
    </div>`;
  }

  protected override render(): unknown {
    const title = this.store.config.title ?? "HAEO forecast";
    if (!this.store.hasData) {
      return html`<ha-card>
        <div class="title">${title}</div>
        <div class="empty">
          No forecast data found. Add forecast entities in card config or ensure HAEO output sensors are available.
        </div>
      </ha-card>`;
    }

    const ticks = 6;
    const tickMarks = Array.from({ length: ticks }, (_, idx) => {
      const ratio = idx / (ticks - 1);
      const x =
        this.store.margins.left + ratio * (this.store.width - this.store.margins.left - this.store.margins.right);
      const time = this.store.xDomain.min + ratio * (this.store.xDomain.max - this.store.xDomain.min);
      return {
        x,
        label: new Date(time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
    });

    return html`
      <ha-card>
        <div class="title">${title}</div>
        <svg
          viewBox="0 0 ${this.store.width} ${this.store.height}"
          height=${this.store.height}
          @pointermove=${(event: PointerEvent) => this.onPointerMove(event)}
          @pointerleave=${() => this.onPointerLeave()}
        >
          ${tickMarks.map(
            (tick) =>
              svg`<line class="grid" x1=${tick.x} y1=${this.store.margins.top} x2=${tick.x} y2=${this.store.height - this.store.margins.bottom}></line>`
          )}
          ${this.renderLaneGraphics()}
          ${tickMarks.map(
            (tick) =>
              svg`<text class="axisLabel" x=${tick.x} y=${this.store.height - this.store.margins.bottom + 18} text-anchor="middle">${tick.label}</text>`
          )}
          ${this.store.hoverX !== null
            ? svg`<line class="hoverLine" x1=${this.store.hoverX} y1=${this.store.margins.top} x2=${this.store.hoverX} y2=${this.store.height - this.store.margins.bottom}></line>`
            : nothing}
        </svg>
        ${this.renderLegend()} ${this.renderTooltip()}
      </ha-card>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "haeo-forecast-card": HaeoForecastCard;
  }
}
