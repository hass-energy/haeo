import { computed, makeAutoObservable } from "mobx";

import { clamp, linearScale, linePath, nearestArrayIndex, stepAreaPath, stepPath } from "./geometry";
import { classifyPowerSeries } from "./power-series-classification";
import { normalizeSeries } from "./series";
import type { HassLike } from "./series";
import type {
  ChartMargins,
  ForecastCardConfig,
  ForecastSeries,
  LaneBounds,
  MotionMode,
  PowerDisplayMode,
} from "./types";

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
  hoveredLegendElement: string | null = null;
  hiddenSeriesKeys = new Set<string>();
  forcedVisibleSeriesKeys = new Set<string>();
  powerDisplayModeOverride: PowerDisplayMode | null = null;

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

  responsiveHeight(width: number): number {
    if (this.config.height !== undefined) {
      return this.config.height;
    }
    return Math.max(260, Math.min(520, Math.round(width * 0.52)));
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

  setHoveredLegendElement(elementName: string | null): void {
    this.hoveredLegendElement = elementName;
  }

  toggleSeriesVisibility(key: string): void {
    if (this.hiddenSeriesKeys.has(key)) {
      this.hiddenSeriesKeys.delete(key);
      this.forcedVisibleSeriesKeys.add(key);
      return;
    }
    this.hiddenSeriesKeys.add(key);
    this.forcedVisibleSeriesKeys.delete(key);
    if (this.highlightedSeries === key) {
      this.highlightedSeries = null;
    }
  }

  toggleElementVisibility(elementName: string): void {
    const keys = this.legendSeries.filter((series) => series.elementName === elementName).map((series) => series.key);
    if (keys.length === 0) {
      return;
    }
    const allHidden = keys.every((key) => this.hiddenSeriesKeys.has(key));
    if (allHidden) {
      for (const key of keys) {
        this.hiddenSeriesKeys.delete(key);
        this.forcedVisibleSeriesKeys.add(key);
      }
      return;
    }
    for (const key of keys) {
      this.hiddenSeriesKeys.add(key);
      this.forcedVisibleSeriesKeys.delete(key);
      if (this.highlightedSeries === key) {
        this.highlightedSeries = null;
      }
    }
  }

  togglePowerDisplayMode(): void {
    this.powerDisplayModeOverride = this.powerDisplayMode === "opposed" ? "overlay" : "opposed";
  }

  get powerDisplayMode(): PowerDisplayMode {
    return this.powerDisplayModeOverride ?? this.config.power_display_mode ?? "opposed";
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
      top: compact ? 20 : 26,
      right: compact ? 46 : 74,
      bottom: compact ? 42 : 50,
      left: compact ? 44 : 58,
    };
  }

  get normalizedSeries(): ForecastSeries[] {
    return normalizeSeries(this.hass, this.config);
  }

  get legendSeries(): ForecastSeries[] {
    this.applyDefaultHiddenSeries();
    return this.normalizedSeries.filter((series) => VISIBLE_LANES.has(series.lane));
  }

  get visibleSeries(): ForecastSeries[] {
    return this.legendSeries.filter((series) => !this.hiddenSeriesKeys.has(series.key));
  }

  get powerSeries(): ForecastSeries[] {
    return this.visibleSeries.filter((series) => series.lane === "power");
  }

  get orderedPowerSeries(): ForecastSeries[] {
    return [...this.powerSeries].sort((a, b) => {
      const ca = classifyPowerSeries(a);
      const cb = classifyPowerSeries(b);
      const aSub = ca.subgroup === "potential" ? 0 : 1;
      const bSub = cb.subgroup === "potential" ? 0 : 1;
      if (aSub !== bSub) {
        return aSub - bSub;
      }
      const aGroup = ca.group === "production" ? 0 : ca.group === "consumption" ? 1 : 2;
      const bGroup = cb.group === "production" ? 0 : cb.group === "consumption" ? 1 : 2;
      if (aGroup !== bGroup) {
        return aGroup - bGroup;
      }
      return a.label.localeCompare(b.label);
    });
  }

  get priceSeries(): ForecastSeries[] {
    return this.visibleSeries.filter((series) => series.lane === "price");
  }

  get socSeries(): ForecastSeries[] {
    return this.visibleSeries.filter((series) => series.lane === "soc");
  }

  get hasData(): boolean {
    return this.legendSeries.length > 0;
  }

  get hasPlottedData(): boolean {
    return this.visibleSeries.length > 0;
  }

  get focusedElementSeriesKeys(): Set<string> {
    if (this.hoveredLegendElement === null) {
      return new Set();
    }
    const focused = new Set<string>();
    for (const series of this.visibleSeries) {
      if (series.elementName === this.hoveredLegendElement) {
        focused.add(series.key);
      }
    }
    return focused;
  }

  get xDomain(): { min: number; max: number; step: number } {
    if (!this.hasPlottedData) {
      const now = this.nowMs;
      return { min: now, max: now + 60_000, step: 60_000 };
    }
    const series = this.visibleSeries;
    if (series.length === 0) {
      const now = this.nowMs;
      return { min: now, max: now + 60_000, step: 60_000 };
    }

    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    let step = Number.POSITIVE_INFINITY;
    for (const item of series) {
      if (item.times.length < 2) {
        continue;
      }
      const first = item.times[0];
      const second = item.times[1];
      const last = item.times[item.times.length - 1];
      if (first === undefined || second === undefined || last === undefined) {
        continue;
      }
      min = Math.min(min, first);
      max = Math.max(max, last);
      step = Math.min(step, Math.max(1, second - first));
    }
    if (!Number.isFinite(min) || !Number.isFinite(max) || !Number.isFinite(step)) {
      const now = this.nowMs;
      return { min: now, max: now + 60_000, step: 60_000 };
    }
    return { min, max, step };
  }

  get hasUniformTimeline(): boolean {
    const firstSeries = this.visibleSeries[0];
    if (!firstSeries || firstSeries.times.length < 3) {
      return true;
    }
    const base = (firstSeries.times[1] ?? 0) - (firstSeries.times[0] ?? 0);
    if (base <= 0) {
      return false;
    }
    for (let idx = 2; idx < firstSeries.times.length; idx += 1) {
      const prev = firstSeries.times[idx - 1] ?? 0;
      const curr = firstSeries.times[idx] ?? 0;
      if (Math.abs(curr - prev - base) > 1) {
        return false;
      }
    }
    return true;
  }

  get animatedOffsetMs(): number {
    if (this.motionMode === "off") {
      return 0;
    }
    const prefersReducedMotion = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
    if (this.motionMode === "reduced" || prefersReducedMotion) {
      return 0;
    }
    if (!this.hasUniformTimeline) {
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
    min = Math.min(min, 0);
    max = Math.max(max, 0);
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
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    for (const series of this.orderedPowerSeries) {
      for (const value of series.values) {
        const transformed = this.powerValueForDisplay(series, value);
        min = Math.min(min, transformed);
        max = Math.max(max, transformed);
      }
    }
    if (!Number.isFinite(min) || !Number.isFinite(max)) {
      return { min: -1, max: 1 };
    }
    min = Math.min(min, 0);
    max = Math.max(max, 0);
    if (min === max) {
      const delta = Math.max(1, Math.abs(min) * 0.15);
      return { min: min - delta, max: max + delta };
    }
    const padding = Math.max(0.1, (max - min) * 0.08);
    return { min: min - padding, max: max + padding };
  }

  get priceBounds(): LaneBounds {
    return this._bounds(this.priceSeries, { min: 0, max: 1 });
  }

  get socBounds(): LaneBounds {
    return { min: 0, max: 100 };
  }

  yScalePower(value: number): number {
    return linearScale(value, this.powerBounds.min, this.powerBounds.max, this.plotBottom, this.plotTop);
  }

  yScalePrice(value: number): number {
    const zeroY = this.yScalePower(0);
    if (value >= 0) {
      const positiveMax = Math.max(this.priceBounds.max, 0.001);
      return linearScale(value, 0, positiveMax, zeroY, this.plotTop);
    }
    const negativeMin = Math.min(this.priceBounds.min, -0.001);
    return linearScale(value, negativeMin, 0, this.plotBottom, zeroY);
  }

  yScaleSoc(value: number): number {
    const zeroY = this.yScalePower(0);
    return linearScale(value, this.socBounds.min, this.socBounds.max, zeroY, this.plotTop);
  }

  get isHoverInPlot(): boolean {
    if (this.pointerX === null || this.pointerY === null) {
      return false;
    }
    return (
      this.pointerX >= this.margins.left &&
      this.pointerX <= this.width - this.margins.right &&
      this.pointerY >= this.plotTop &&
      this.pointerY <= this.plotBottom
    );
  }

  get powerShapes(): Array<{ key: string; color: string; d: string }> {
    const seriesList = this.orderedPowerSeries;
    const firstSeries = seriesList[0];
    if (!firstSeries) {
      return [];
    }
    const horizonCount = firstSeries.times.length;
    const positive = new Float64Array(horizonCount);
    const negative = new Float64Array(horizonCount);

    return seriesList.map((series) => {
      const lower = new Float64Array(horizonCount);
      const upper = new Float64Array(horizonCount);
      for (let idx = 0; idx < horizonCount; idx += 1) {
        const raw = series.values[idx] ?? 0;
        const value = this.powerValueForDisplay(series, raw);
        if (value >= 0) {
          lower[idx] = positive[idx] ?? 0;
          const next = (positive[idx] ?? 0) + value;
          upper[idx] = next;
          positive[idx] = next;
        } else {
          lower[idx] = negative[idx] ?? 0;
          const next = (negative[idx] ?? 0) + value;
          upper[idx] = next;
          negative[idx] = next;
        }
      }
      return {
        key: series.key,
        color: series.color,
        d: stepAreaPath(
          series.times,
          lower,
          upper,
          (time) => this.xScale(time),
          (value) => this.yScalePower(value)
        ),
      };
    });
  }

  get hoveredPowerSeriesKeys(): Set<string> {
    if (!this.isHoverInPlot) {
      return new Set();
    }
    const time = this.hoverTimeMs;
    if (time === null || this.pointerY === null) {
      return new Set();
    }
    const hovered = new Set<string>();
    const powerSeries = this.orderedPowerSeries;
    if (powerSeries.length === 0) {
      return hovered;
    }
    const idxBySeries = this.hoverIndices;
    let positiveStack = 0;
    let negativeStack = 0;
    for (const series of powerSeries) {
      const idx = idxBySeries.get(series.key) ?? 0;
      const raw = series.values[idx] ?? 0;
      const value = this.powerValueForDisplay(series, raw);
      if (Math.abs(value) < 1e-6) {
        continue;
      }
      let lower = 0;
      let upper = 0;
      if (value >= 0) {
        lower = positiveStack;
        upper = positiveStack + value;
        positiveStack = upper;
      } else {
        lower = negativeStack;
        upper = negativeStack + value;
        negativeStack = upper;
      }
      const y1 = this.yScalePower(lower);
      const y2 = this.yScalePower(upper);
      const top = Math.min(y1, y2);
      const bottom = Math.max(y1, y2);
      if (this.pointerY >= top && this.pointerY <= bottom) {
        hovered.add(series.key);
      }
    }

    // Also highlight "potential" sources at this timestamp when they contribute.
    for (const series of powerSeries) {
      const category = classifyPowerSeries(series);
      if (category.subgroup !== "potential") {
        continue;
      }
      const idx = idxBySeries.get(series.key) ?? 0;
      const value = Math.abs(series.values[idx] ?? 0);
      if (Math.abs(value) > 1e-6) {
        hovered.add(series.key);
      }
    }
    return hovered;
  }

  get pricePaths(): Array<{ key: string; color: string; d: string }> {
    return this.priceSeries.map((series) => ({
      key: series.key,
      color: series.color,
      d: stepPath(
        series.points,
        (time) => this.xScale(time),
        (value) => this.yScalePrice(value)
      ),
    }));
  }

  get socPaths(): Array<{ key: string; color: string; d: string }> {
    return this.socSeries.map((series) => ({
      key: series.key,
      color: series.color,
      d: linePath(
        series.points,
        (time) => this.xScale(time),
        (value) => this.yScaleSoc(value)
      ),
    }));
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

  get hoverIndices(): Map<string, number> {
    const time = this.hoverTimeMs;
    if (time === null) {
      return new Map();
    }
    const indices = new Map<string, number>();
    for (const series of this.visibleSeries) {
      indices.set(series.key, nearestArrayIndex(series.times, time));
    }
    return indices;
  }

  get tooltipRows(): Array<{ key: string; label: string; value: number; unit: string; color: string; lane: string }> {
    const time = this.hoverTimeMs;
    if (time === null) {
      return [];
    }
    const hoverIndices = this.hoverIndices;
    const rows: Array<{ key: string; label: string; value: number; unit: string; color: string; lane: string }> = [];
    for (const series of this.visibleSeries) {
      const idx = hoverIndices.get(series.key) ?? 0;
      rows.push({
        key: series.key,
        label: series.label,
        value:
          series.lane === "power"
            ? this.powerValueForDisplay(series, series.values[idx] ?? 0)
            : (series.values[idx] ?? 0),
        unit: series.unit,
        color: series.color,
        lane: series.lane,
      });
    }
    const laneOrder = new Map<string, number>([
      ["power", 0],
      ["price", 1],
      ["soc", 2],
    ]);
    return rows.sort((a, b) => {
      const la = laneOrder.get(a.lane) ?? 9;
      const lb = laneOrder.get(b.lane) ?? 9;
      if (la !== lb) {
        return la - lb;
      }
      return Math.abs(b.value) - Math.abs(a.value);
    });
  }

  get tooltipTotals(): Array<{ lane: string; value: number; unit: string }> {
    const time = this.hoverTimeMs;
    if (time === null) {
      return [];
    }
    const hoverIndices = this.hoverIndices;
    const totals = new Map<string, { value: number; unit: string }>();
    for (const series of this.visibleSeries) {
      const idx = hoverIndices.get(series.key) ?? 0;
      const existing = totals.get(series.lane) ?? { value: 0, unit: series.unit };
      const value =
        series.lane === "power"
          ? this.powerValueForDisplay(series, series.values[idx] ?? 0)
          : (series.values[idx] ?? 0);
      totals.set(series.lane, {
        value: existing.value + value,
        unit: existing.unit || series.unit,
      });
    }
    return [...totals.entries()].map(([lane, total]) => ({
      lane,
      value: total.value,
      unit: total.unit,
    }));
  }

  get tooltipEmphasisKeys(): Set<string> {
    const keys = new Set<string>();
    for (const key of this.hoveredPowerSeriesKeys) {
      keys.add(key);
    }
    if (this.highlightedSeries) {
      keys.add(this.highlightedSeries);
    }
    return keys;
  }

  private powerValueForDisplay(series: ForecastSeries, value: number): number {
    const magnitude = Math.abs(value);
    if (this.powerDisplayMode === "overlay") {
      return magnitude;
    }
    const category = classifyPowerSeries(series);
    if (category.group === "consumption") {
      return -magnitude;
    }
    return magnitude;
  }

  private applyDefaultHiddenSeries(): void {
    for (const series of this.normalizedSeries) {
      if (series.lane !== "power") {
        continue;
      }
      const isGrid = series.elementName.toLowerCase().includes("grid");
      const category = classifyPowerSeries(series);
      if (!isGrid || category.subgroup !== "potential") {
        continue;
      }
      if (!this.forcedVisibleSeriesKeys.has(series.key)) {
        this.hiddenSeriesKeys.add(series.key);
      }
    }
  }
}
