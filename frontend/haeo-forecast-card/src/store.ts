import { computed, makeAutoObservable } from "mobx";

import { clamp, linearScale, nearestArrayIndex } from "./geometry";
import { normalizeSeries } from "./series";
import type { HassLike } from "./series";
import type { ChartMargins, ForecastCardConfig, ForecastSeries, LaneBounds, MotionMode } from "./types";

const DEFAULT_HEIGHT = 360;
const VISIBLE_LANES = new Set(["power", "price", "soc"]);

export class ForecastCardStore {
  hass: HassLike | null = null;
  config: ForecastCardConfig = { type: "custom:haeo-forecast-card" };
  width = 640;
  height = DEFAULT_HEIGHT;
  pointerX: number | null = null;
  pointerY: number | null = null;
  nowMs = Date.now();
  highlightedSeries: string | null = null;

  constructor() {
    makeAutoObservable(this, {
      margins: computed.struct,
      visibleSeries: computed.struct,
      powerBounds: computed.struct,
      priceBounds: computed.struct,
      socBounds: computed.struct,
      tooltipRows: computed.struct,
    });
  }

  setHass(hass: HassLike): void {
    this.hass = hass;
  }

  setConfig(config: ForecastCardConfig): void {
    this.config = config;
  }

  setSize(width: number, height: number): void {
    this.width = Math.max(240, width);
    this.height = Math.max(220, height);
  }

  setPointer(x: number | null, y: number | null): void {
    this.pointerX = x;
    this.pointerY = y;
  }

  setNow(nowMs: number): void {
    this.nowMs = nowMs;
  }

  setHighlightedSeries(key: string | null): void {
    this.highlightedSeries = key;
  }

  get motionMode(): MotionMode {
    return this.config.animation_mode ?? "smooth";
  }

  get animationSpeed(): number {
    const raw = this.config.animation_speed ?? 1;
    return clamp(raw, 0.2, 3);
  }

  get chartHeight(): number {
    return this.config.height ?? DEFAULT_HEIGHT;
  }

  get margins(): ChartMargins {
    const compact = this.width < 400;
    return {
      top: 16,
      right: compact ? 10 : 16,
      bottom: compact ? 34 : 40,
      left: compact ? 40 : 54,
    };
  }

  get normalizedSeries(): ForecastSeries[] {
    return normalizeSeries(this.hass, this.config);
  }

  get visibleSeries(): ForecastSeries[] {
    return this.normalizedSeries.filter((series) => VISIBLE_LANES.has(series.lane));
  }

  get powerSeries(): ForecastSeries[] {
    return this.visibleSeries.filter((series) => series.lane === "power");
  }

  get priceSeries(): ForecastSeries[] {
    return this.visibleSeries.filter((series) => series.lane === "price");
  }

  get socSeries(): ForecastSeries[] {
    return this.visibleSeries.filter((series) => series.lane === "soc");
  }

  get hasData(): boolean {
    return this.visibleSeries.length > 0;
  }

  get xDomain(): { min: number; max: number; step: number } {
    if (!this.hasData) {
      const now = this.nowMs;
      return { min: now, max: now + 60_000, step: 60_000 };
    }
    const firstSeries = this.visibleSeries[0];
    if (!firstSeries) {
      const now = this.nowMs;
      return { min: now, max: now + 60_000, step: 60_000 };
    }
    const points = firstSeries.points;
    const firstPoint = points[0];
    const secondPoint = points[1];
    const lastPoint = points[points.length - 1];
    if (!firstPoint || !lastPoint) {
      const now = this.nowMs;
      return { min: now, max: now + 60_000, step: 60_000 };
    }
    const min = firstPoint.time;
    const max = lastPoint.time;
    const step = secondPoint ? Math.max(1, secondPoint.time - firstPoint.time) : 60_000;
    return { min, max, step };
  }

  get animatedOffsetMs(): number {
    if (this.motionMode === "off") {
      return 0;
    }
    const prefersReducedMotion = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
    if (this.motionMode === "reduced" || prefersReducedMotion) {
      return 0;
    }
    const { min, step } = this.xDomain;
    const elapsed = (this.nowMs - min) * this.animationSpeed;
    if (elapsed <= 0 || step <= 0) {
      return 0;
    }
    return elapsed % step;
  }

  xScale(time: number): number {
    const { min, max } = this.xDomain;
    const innerWidth = this.width - this.margins.left - this.margins.right;
    return linearScale(time - this.animatedOffsetMs, min, max, this.margins.left, this.margins.left + innerWidth);
  }

  private _bounds(seriesList: ForecastSeries[], fallback: LaneBounds): LaneBounds {
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    for (const series of seriesList) {
      for (const value of series.values) {
        min = Math.min(min, value);
        max = Math.max(max, value);
      }
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      return fallback;
    }
    if (min === max) {
      const delta = Math.max(1, Math.abs(min) * 0.15);
      return { min: min - delta, max: max + delta };
    }
    const padding = Math.max(0.1, (max - min) * 0.08);
    return { min: min - padding, max: max + padding };
  }

  get plotTop(): number {
    return this.margins.top;
  }

  get plotBottom(): number {
    return this.height - this.margins.bottom;
  }

  get powerBounds(): LaneBounds {
    return this._bounds(this.powerSeries, { min: 0, max: 1 });
  }

  get priceBounds(): LaneBounds {
    return this._bounds(this.priceSeries, { min: 0, max: 1 });
  }

  get socBounds(): LaneBounds {
    return this._bounds(this.socSeries, { min: 0, max: 100 });
  }

  yScalePower(value: number): number {
    return linearScale(value, this.powerBounds.min, this.powerBounds.max, this.plotBottom, this.plotTop);
  }

  yScalePrice(value: number): number {
    const topBandBottom = this.plotTop + (this.plotBottom - this.plotTop) * 0.45;
    return linearScale(value, this.priceBounds.min, this.priceBounds.max, topBandBottom, this.plotTop + 6);
  }

  yScaleSoc(value: number): number {
    const bottomBandTop = this.plotTop + (this.plotBottom - this.plotTop) * 0.5;
    return linearScale(value, this.socBounds.min, this.socBounds.max, this.plotBottom - 6, bottomBandTop);
  }

  get hoverTimeMs(): number | null {
    if (this.pointerX === null) {
      return null;
    }
    const x = clamp(this.pointerX, this.margins.left, this.width - this.margins.right);
    const { min, max } = this.xDomain;
    const innerWidth = this.width - this.margins.left - this.margins.right;
    const ratio = innerWidth > 0 ? (x - this.margins.left) / innerWidth : 0;
    return min + ratio * (max - min) + this.animatedOffsetMs;
  }

  get hoverX(): number | null {
    const time = this.hoverTimeMs;
    return time === null ? null : this.xScale(time);
  }

  get tooltipRows(): Array<{ key: string; label: string; value: number; unit: string; color: string }> {
    const time = this.hoverTimeMs;
    if (time === null) {
      return [];
    }
    const rows: Array<{ key: string; label: string; value: number; unit: string; color: string }> = [];
    for (const series of this.visibleSeries) {
      const idx = nearestArrayIndex(series.times, time);
      rows.push({
        key: series.key,
        label: series.label,
        value: series.values[idx] ?? 0,
        unit: series.unit,
        color: series.color,
      });
    }
    return rows.sort((a, b) => b.value - a.value);
  }

  get tooltipTotals(): Array<{ lane: string; value: number; unit: string }> {
    const time = this.hoverTimeMs;
    if (time === null) {
      return [];
    }
    const totals = new Map<string, { value: number; unit: string }>();
    for (const series of this.visibleSeries) {
      const idx = nearestArrayIndex(series.times, time);
      const existing = totals.get(series.lane) ?? { value: 0, unit: series.unit };
      totals.set(series.lane, {
        value: existing.value + (series.values[idx] ?? 0),
        unit: existing.unit || series.unit,
      });
    }
    return [...totals.entries()].map(([lane, total]) => ({
      lane,
      value: total.value,
      unit: total.unit,
    }));
  }
}
