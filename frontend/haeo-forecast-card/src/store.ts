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
type PowerSection = "available" | "produced" | "consumed" | "possible";

export class ForecastCardStore {
  hass: HassLike | null = null;
  config: ForecastCardConfig = { type: "custom:haeo-forecast-card" };
  normalizedSeriesCache: ForecastSeries[] = [];
  bidirectionalSeriesCache = new Map<string, boolean>();
  powerBoundsCache: LaneBounds = { min: -1, max: 1 };
  width = 640;
  height = DEFAULT_HEIGHT;
  pointerX: number | null = null;
  pointerY: number | null = null;
  nowMs = Date.now();
  highlightedSeries: string | null = null;
  hoveredLegendElement: string | null = null;
  hiddenSeriesKeys = new Set<string>();
  forcedVisibleSeriesKeys = new Set<string>();
  visibilityRevision = 0;
  powerDisplayModeOverride: PowerDisplayMode | null = null;

  constructor() {
    makeAutoObservable(this, {
      margins: computed.struct,
      normalizedSeries: computed.struct,
      visibleSeries: computed.struct,
      powerBounds: computed.struct,
      priceBounds: computed.struct,
      socBounds: computed.struct,
      tooltipRows: computed.struct,
    });
  }

  setHass(hass: HassLike): void {
    this.hass = hass;
    this.refreshNormalizedSeries();
  }

  setConfig(config: ForecastCardConfig): void {
    this.config = config;
    this.refreshNormalizedSeries();
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
      this.visibilityRevision += 1;
      this.recomputePowerBounds();
      return;
    }
    this.hiddenSeriesKeys.add(key);
    this.forcedVisibleSeriesKeys.delete(key);
    this.visibilityRevision += 1;
    this.recomputePowerBounds();
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
      this.visibilityRevision += 1;
      this.recomputePowerBounds();
      return;
    }
    for (const key of keys) {
      this.hiddenSeriesKeys.add(key);
      this.forcedVisibleSeriesKeys.delete(key);
      if (this.highlightedSeries === key) {
        this.highlightedSeries = null;
      }
    }
    this.visibilityRevision += 1;
    this.recomputePowerBounds();
  }

  togglePowerDisplayMode(): void {
    this.powerDisplayModeOverride = this.powerDisplayMode === "opposed" ? "overlay" : "opposed";
    this.recomputePowerBounds();
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
    return this.normalizedSeriesCache;
  }

  get legendSeries(): ForecastSeries[] {
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
      const sectionOrder = (series: ForecastSeries): number => {
        const section = this.powerSection(series);
        if (section === "possible") {
          return 0;
        }
        if (section === "available") {
          return 1;
        }
        if (section === "produced") {
          return 2;
        }
        return 3;
      };
      const order = sectionOrder(a) - sectionOrder(b);
      if (order !== 0) {
        return order;
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

  get locale(): string {
    return this.hass?.language ?? this.hass?.locale?.language ?? "en";
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

  private buildXScale(): (time: number) => number {
    const { min, max } = this.xDomain;
    const innerWidth = this.width - this.margins.left - this.margins.right;
    const left = this.margins.left;
    const offset = this.animatedOffsetMs;
    return (time: number) => linearScale(time - offset, min, max, left, left + innerWidth);
  }

  xScale(time: number): number {
    return this.buildXScale()(time);
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
    return this.powerBoundsCache;
  }

  private calculatePowerBounds(): LaneBounds {
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    const firstSeries = this.orderedPowerSeries[0];
    if (!firstSeries) {
      return { min: -1, max: 1 };
    }
    const sectionStacks = this.emptySectionStacks(firstSeries.times.length);
    for (const series of this.orderedPowerSeries) {
      const section = this.powerSection(series);
      const stack = sectionStacks[section];
      for (let idx = 0; idx < firstSeries.times.length; idx += 1) {
        const transformed = this.powerValueForDisplay(series, series.values[idx] ?? 0);
        const next = (stack[idx] ?? 0) + transformed;
        stack[idx] = next;
        min = Math.min(min, next);
        max = Math.max(max, next);
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

  get powerShapes(): Array<{ key: string; color: string; d: string; isPotential: boolean }> {
    const seriesList = this.orderedPowerSeries;
    const firstSeries = seriesList[0];
    if (!firstSeries) {
      return [];
    }
    const xScale = this.buildXScale();
    const { min: powerMin, max: powerMax } = this.powerBounds;
    const plotBottom = this.plotBottom;
    const plotTop = this.plotTop;
    const yScalePower = (value: number): number => linearScale(value, powerMin, powerMax, plotBottom, plotTop);
    const horizonCount = firstSeries.times.length;
    const stacks = this.emptySectionStacks(horizonCount);

    return seriesList.map((series) => {
      const category = classifyPowerSeries(series);
      const section = this.powerSection(series);
      const stack = stacks[section];
      const lower = new Float64Array(horizonCount);
      const upper = new Float64Array(horizonCount);
      for (let idx = 0; idx < horizonCount; idx += 1) {
        const value = this.powerValueForDisplay(series, series.values[idx] ?? 0);
        lower[idx] = stack[idx] ?? 0;
        const next = (stack[idx] ?? 0) + value;
        upper[idx] = next;
        stack[idx] = next;
      }
      return {
        key: series.key,
        color: series.color,
        isPotential: category.subgroup === "potential",
        d: stepAreaPath(
          series.times,
          lower,
          upper,
          (time) => xScale(time),
          (value) => yScalePower(value)
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
    const { min: powerMin, max: powerMax } = this.powerBounds;
    const plotBottom = this.plotBottom;
    const plotTop = this.plotTop;
    const yScalePower = (value: number): number => linearScale(value, powerMin, powerMax, plotBottom, plotTop);
    const idxBySeries = this.hoverIndices;
    const stackedAtHover = new Map<PowerSection, number>([
      ["available", 0],
      ["produced", 0],
      ["consumed", 0],
      ["possible", 0],
    ]);
    for (const series of powerSeries) {
      const idx = idxBySeries.get(series.key) ?? 0;
      const raw = series.values[idx] ?? 0;
      const value = this.powerValueForDisplay(series, raw);
      if (Math.abs(value) < 1e-6) {
        continue;
      }
      const section = this.powerSection(series);
      const lower = stackedAtHover.get(section) ?? 0;
      const upper = lower + value;
      stackedAtHover.set(section, upper);
      const y1 = yScalePower(lower);
      const y2 = yScalePower(upper);
      const top = Math.min(y1, y2);
      const bottom = Math.max(y1, y2);
      if (this.pointerY >= top && this.pointerY <= bottom) {
        hovered.add(series.key);
      }
    }

    return hovered;
  }

  get pricePaths(): Array<{ key: string; color: string; d: string }> {
    const xScale = this.buildXScale();
    const { min: powerMin, max: powerMax } = this.powerBounds;
    const { min: priceMin, max: priceMax } = this.priceBounds;
    const plotBottom = this.plotBottom;
    const plotTop = this.plotTop;
    const yScalePower = (value: number): number => linearScale(value, powerMin, powerMax, plotBottom, plotTop);
    const zeroY = yScalePower(0);
    const yScalePrice = (value: number): number => {
      if (value >= 0) {
        const positiveMax = Math.max(priceMax, 0.001);
        return linearScale(value, 0, positiveMax, zeroY, plotTop);
      }
      const negativeMin = Math.min(priceMin, -0.001);
      return linearScale(value, negativeMin, 0, plotBottom, zeroY);
    };
    return this.priceSeries.map((series) => ({
      key: series.key,
      color: series.color,
      d: stepPath(
        series.points,
        (time) => xScale(time),
        (value) => yScalePrice(value)
      ),
    }));
  }

  get socPaths(): Array<{ key: string; color: string; d: string }> {
    const xScale = this.buildXScale();
    const { min: powerMin, max: powerMax } = this.powerBounds;
    const plotBottom = this.plotBottom;
    const plotTop = this.plotTop;
    const yScalePower = (value: number): number => linearScale(value, powerMin, powerMax, plotBottom, plotTop);
    const zeroY = yScalePower(0);
    const socMin = this.socBounds.min;
    const socMax = this.socBounds.max;
    const yScaleSoc = (value: number): number => linearScale(value, socMin, socMax, zeroY, plotTop);
    return this.socSeries.map((series) => ({
      key: series.key,
      color: series.color,
      d: linePath(
        series.points,
        (time) => xScale(time),
        (value) => yScaleSoc(value)
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
    const sharedTimeline = this.sharedTimeline;
    if (sharedTimeline) {
      const nearestIdx = nearestArrayIndex(sharedTimeline, time);
      const stepIdx = this.stepArrayIndex(sharedTimeline, time);
      return new Map(
        this.visibleSeries.map((series) => [series.key, series.drawType === "step" ? stepIdx : nearestIdx])
      );
    }
    const indices = new Map<string, number>();
    for (const series of this.visibleSeries) {
      const idx =
        series.drawType === "step" ? this.stepArrayIndex(series.times, time) : nearestArrayIndex(series.times, time);
      indices.set(series.key, idx);
    }
    return indices;
  }

  get sharedTimeline(): Float64Array | null {
    const first = this.visibleSeries[0];
    if (!first) {
      return null;
    }
    for (let seriesIdx = 1; seriesIdx < this.visibleSeries.length; seriesIdx += 1) {
      const series = this.visibleSeries[seriesIdx];
      if (series?.times.length !== first.times.length) {
        return null;
      }
      for (let idx = 0; idx < first.times.length; idx += 1) {
        if (series.times[idx] !== first.times[idx]) {
          return null;
        }
      }
    }
    return first.times;
  }

  get tooltipRows(): Array<{ key: string; label: string; value: number; unit: string; color: string; lane: string }> {
    const time = this.hoverTimeMs;
    if (time === null) {
      return [];
    }
    const hoverIndices = this.hoverIndices;
    const rows: Array<{ key: string; label: string; value: number; unit: string; color: string; lane: string }> = [];
    const nameCounts = new Map<string, number>();
    for (const series of this.visibleSeries) {
      const key = series.label.trim().toLowerCase();
      nameCounts.set(key, (nameCounts.get(key) ?? 0) + 1);
    }
    for (const series of this.visibleSeries) {
      const idx = hoverIndices.get(series.key) ?? 0;
      const section = this.tooltipSection(series);
      const duplicateLabel = (nameCounts.get(series.label.trim().toLowerCase()) ?? 0) > 1;
      rows.push({
        key: series.key,
        label: this.tooltipDisplayLabel(series, section, duplicateLabel),
        value:
          series.lane === "power"
            ? this.powerValueForDisplay(series, series.values[idx] ?? 0)
            : (series.values[idx] ?? 0),
        unit: series.unit,
        color: series.color,
        lane: section,
      });
    }
    const laneOrder = new Map<string, number>([
      ["Produced", 0],
      ["Available", 1],
      ["Consumed", 2],
      ["Possible", 3],
      ["Price", 4],
      ["State of charge", 5],
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
    const sectionOrder = new Map<string, number>([
      ["Produced", 0],
      ["Available", 1],
      ["Consumed", 2],
      ["Possible", 3],
    ]);
    const totals = new Map<string, { value: number; unit: string }>();
    for (const series of this.visibleSeries) {
      if (series.lane !== "power") {
        continue;
      }
      const idx = hoverIndices.get(series.key) ?? 0;
      const section = this.tooltipSection(series);
      const existing = totals.get(section) ?? { value: 0, unit: series.unit };
      const value = this.powerValueForDisplay(series, series.values[idx] ?? 0);
      totals.set(section, {
        value: existing.value + value,
        unit: existing.unit || series.unit,
      });
    }
    return [...totals.entries()]
      .filter(([, total]) => Math.abs(total.value) > 1e-9)
      .sort((a, b) => (sectionOrder.get(a[0]) ?? 9) - (sectionOrder.get(b[0]) ?? 9))
      .map(([lane, total]) => ({ lane, value: total.value, unit: total.unit }));
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
    if (this.bidirectionalSeriesCache.get(series.key)) {
      return value;
    }
    const category = classifyPowerSeries(series);
    if (category.group === "consumption") {
      return -magnitude;
    }
    return magnitude;
  }

  private applyDefaultHiddenSeries(): void {
    let hiddenChanged = false;
    const directionalByElement = new Map<string, { hasProd: boolean; hasCons: boolean }>();
    for (const series of this.normalizedSeries) {
      if (series.lane !== "power") {
        continue;
      }
      const category = classifyPowerSeries(series);
      const existing = directionalByElement.get(series.elementName) ?? { hasProd: false, hasCons: false };
      if (category.group === "production" && category.subgroup === "utilization") {
        existing.hasProd = true;
      }
      if (category.group === "consumption" && category.subgroup === "utilization") {
        existing.hasCons = true;
      }
      directionalByElement.set(series.elementName, existing);
    }
    for (const series of this.normalizedSeries) {
      if (series.lane !== "power") {
        continue;
      }
      const isGrid = series.elementName.toLowerCase().includes("grid");
      const category = classifyPowerSeries(series);
      const output = series.outputName.toLowerCase();
      const hasDirectionalPair = directionalByElement.get(series.elementName);
      const hideByDefault =
        (isGrid && category.subgroup === "potential") ||
        ((output.includes("active") || output.includes("balance")) &&
          Boolean(hasDirectionalPair?.hasProd && hasDirectionalPair.hasCons));
      if (hideByDefault && !this.forcedVisibleSeriesKeys.has(series.key)) {
        const before = this.hiddenSeriesKeys.size;
        this.hiddenSeriesKeys.add(series.key);
        hiddenChanged ||= this.hiddenSeriesKeys.size !== before;
      }
    }
    if (hiddenChanged) {
      this.visibilityRevision += 1;
    }
  }

  private refreshNormalizedSeries(): void {
    const nextSeries = normalizeSeries(this.hass, this.config);
    this.normalizedSeriesCache = nextSeries;
    this.rebuildBidirectionalSeriesCache(nextSeries);

    const seriesKeys = new Set(nextSeries.map((series) => series.key));
    this.hiddenSeriesKeys = new Set([...this.hiddenSeriesKeys].filter((key) => seriesKeys.has(key)));
    this.forcedVisibleSeriesKeys = new Set([...this.forcedVisibleSeriesKeys].filter((key) => seriesKeys.has(key)));
    if (this.highlightedSeries && !seriesKeys.has(this.highlightedSeries)) {
      this.highlightedSeries = null;
    }
    if (this.hoveredLegendElement) {
      const hasHoveredElement = nextSeries.some((series) => series.elementName === this.hoveredLegendElement);
      if (!hasHoveredElement) {
        this.hoveredLegendElement = null;
      }
    }

    this.applyDefaultHiddenSeries();
    this.recomputePowerBounds();
  }

  private rebuildBidirectionalSeriesCache(seriesList: ForecastSeries[]): void {
    const byKey = new Map<string, boolean>();
    for (const series of seriesList) {
      let hasPositive = false;
      let hasNegative = false;
      for (const value of series.values) {
        if (value > 0) {
          hasPositive = true;
        } else if (value < 0) {
          hasNegative = true;
        }
        if (hasPositive && hasNegative) {
          break;
        }
      }
      byKey.set(series.key, hasPositive && hasNegative);
    }
    this.bidirectionalSeriesCache = byKey;
  }

  private recomputePowerBounds(): void {
    this.powerBoundsCache = this.calculatePowerBounds();
  }

  private tooltipSection(series: ForecastSeries): string {
    if (series.lane === "price") {
      return "Price";
    }
    if (series.lane === "soc") {
      return "State of charge";
    }
    const category = classifyPowerSeries(series);
    if (category.group === "production") {
      return category.subgroup === "potential" ? "Available" : "Produced";
    }
    if (category.group === "consumption") {
      return category.subgroup === "potential" ? "Possible" : "Consumed";
    }
    return "Consumed";
  }

  private tooltipDisplayLabel(series: ForecastSeries, section: string, duplicateLabel: boolean): string {
    const name = series.label.trim();
    if (section === "Price") {
      const output = series.outputName.toLowerCase();
      if (output.includes("import")) {
        return `${name} (import)`;
      }
      if (output.includes("export")) {
        return `${name} (export)`;
      }
      return name;
    }
    if (series.lane !== "power") {
      return duplicateLabel ? `${name} (${this.prettifyOutput(series.outputName)})` : name;
    }
    const lower = name.toLowerCase();
    if (
      lower.includes("import") ||
      lower.includes("export") ||
      lower.includes("charge") ||
      lower.includes("discharge")
    ) {
      return duplicateLabel ? `${name} (${this.prettifyOutput(series.outputName)})` : name;
    }
    return duplicateLabel
      ? `${name} (${this.prettifyOutput(series.outputName)})`
      : `${name} (${section.toLowerCase()})`;
  }

  private prettifyOutput(outputName: string): string {
    return outputName.replace(/_/g, " ").trim().toLowerCase();
  }

  private stepArrayIndex(times: Float64Array, time: number): number {
    const length = times.length;
    if (length <= 1) {
      return 0;
    }
    let low = 0;
    let high = length;
    while (low < high) {
      const mid = (low + high) >>> 1;
      const midValue = times[mid] ?? 0;
      if (midValue <= time) {
        low = mid + 1;
      } else {
        high = mid;
      }
    }
    const idx = low - 1;
    if (idx < 0) {
      return 0;
    }
    if (idx >= length) {
      return length - 1;
    }
    return idx;
  }

  private powerSection(series: ForecastSeries): PowerSection {
    const category = classifyPowerSeries(series);
    if (category.group === "production") {
      return category.subgroup === "potential" ? "available" : "produced";
    }
    if (category.group === "consumption") {
      return category.subgroup === "potential" ? "possible" : "consumed";
    }
    return "consumed";
  }

  private emptySectionStacks(length = 0): Record<PowerSection, Float64Array> {
    return {
      available: new Float64Array(length),
      produced: new Float64Array(length),
      consumed: new Float64Array(length),
      possible: new Float64Array(length),
    };
  }
}
