import { computed, makeAutoObservable } from "mobx";

import { clamp, linearScale } from "./geometry";
import { computeHoverIndices, sharedTimeline } from "./hover";
import { calculatePowerBounds, powerValueForDisplay } from "./power-display";
import { classifyPowerSeries, isPowerPotentialSeries, powerPairKey } from "./power-series-classification";
import { normalizeSeries } from "./series";
import type { HassLike } from "./series";
import type { LineSvgPath, PowerShape } from "./store-paths";
import { computeHoveredPowerKeys, computePowerShapes, computePricePaths, computeSocPaths } from "./store-paths";
import { buildTooltipRows, type TooltipSectionId } from "./tooltip-helpers";
import type { ChartMargins, ForecastCardConfig, ForecastSeries, LaneBounds, PowerDisplayMode } from "./types";

const DEFAULT_HEIGHT = 360;
const VISIBLE_LANES = new Set(["power", "price", "soc"]);
const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
const HORIZON_ANIMATION_MS = 220;
const BASE_HORIZON_OPTIONS_MS = [
  15 * MINUTE_MS,
  30 * MINUTE_MS,
  HOUR_MS,
  2 * HOUR_MS,
  4 * HOUR_MS,
  8 * HOUR_MS,
  12 * HOUR_MS,
] as const;

function between(min: number, value: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export type HorizonOption = number | null;

export function formatHorizonDuration(durationMs: number): string {
  if (durationMs < HOUR_MS) {
    return `${Math.round(durationMs / MINUTE_MS)}m`;
  }
  if (durationMs < DAY_MS) {
    return `${Math.round(durationMs / HOUR_MS)}h`;
  }
  const days = durationMs / DAY_MS;
  return Number.isInteger(days) ? `${days}d` : `${days.toFixed(1)}d`;
}

interface Domain {
  min: number;
  max: number;
  step: number;
}

interface HorizonAnimation {
  from: Domain;
  to: Domain;
  startMs: number;
}

interface PlotPaths {
  powerShapes: PowerShape[];
  pricePaths: LineSvgPath[];
  socPaths: LineSvgPath[];
}

export class ForecastCardStore {
  hass: HassLike | null = null;
  config: ForecastCardConfig = { type: "custom:haeo-forecast-card" };
  normalizedSeriesCache: ForecastSeries[] = [];
  powerBoundsCache: LaneBounds = { min: -1, max: 1 };
  cardWidth = 640;
  width = 640;
  height = DEFAULT_HEIGHT;
  pointerX: number | null = null;
  pointerY: number | null = null;
  highlightedSeries: string | null = null;
  highlightedSeriesGroupKeys = new Set<string>();
  hoveredLegendElement: string | null = null;
  hiddenSeriesKeys = new Set<string>();
  forcedVisibleSeriesKeys = new Set<string>();
  visibilityRevision = 0;
  seriesDataRevision = 0;
  powerDisplayModeOverride: PowerDisplayMode | null = null;
  horizonDurationMs: HorizonOption = null;
  horizonRevision = 0;
  horizonAnimation: HorizonAnimation | null = null;
  horizonAnimationNowMs = 0;
  horizonAnimationFrame = 0;
  tooltipVisible = true;
  readonly instanceId: number;
  plotPathsSnapshot: PlotPaths | null = null;
  plotPathsSnapshotKey = "";

  constructor(instanceId = 0) {
    this.instanceId = instanceId;
    makeAutoObservable(this, {
      instanceId: false,
      plotPathsSnapshot: false,
      plotPathsSnapshotKey: false,
      margins: computed.struct,
      normalizedSeries: computed.struct,
      visibleSeries: computed.struct,
      powerBounds: computed.struct,
      priceBounds: computed.struct,
      socBounds: computed.struct,
      tooltipRows: computed.struct,
      cachedXScale: computed,
    });
  }

  // --- Mutations ---

  setHass(hass: HassLike): void {
    this.hass = hass;
    this.refreshNormalizedSeries();
  }

  setConfig(config: ForecastCardConfig): void {
    this.config = config;
    this.refreshNormalizedSeries();
  }

  setSize(width: number, height: number, cardWidth = width): void {
    this.cardWidth = Math.max(240, cardWidth);
    this.width = Math.max(240, width);
    this.height = Math.max(220, height);
  }

  responsiveHeight(width: number): number {
    if (width <= 640) {
      return 680;
    }
    return Math.max(260, Math.min(520, Math.round(width * 0.52)));
  }

  setPointer(x: number | null, y: number | null): void {
    this.pointerX = x;
    this.pointerY = y;
  }

  setHighlightedSeries(key: string | null): void {
    this.highlightedSeries = key;
  }

  setHighlightedSeriesGroup(keys: string[] | null): void {
    this.highlightedSeriesGroupKeys = new Set(keys ?? []);
  }

  setHoveredLegendElement(elementName: string | null): void {
    this.hoveredLegendElement = elementName;
  }

  toggleSeriesVisibility(key: string): void {
    const keys = this.visibilityGroupKeys(key);
    const allHidden = keys.every((seriesKey) => this.hiddenSeriesKeys.has(seriesKey));
    for (const seriesKey of keys) {
      if (allHidden) {
        this.hiddenSeriesKeys.delete(seriesKey);
        this.forcedVisibleSeriesKeys.add(seriesKey);
      } else {
        this.hiddenSeriesKeys.add(seriesKey);
        this.forcedVisibleSeriesKeys.delete(seriesKey);
      }
    }
    this.visibilityRevision += 1;
    this.recomputePowerBounds();
    if (this.highlightedSeries !== null && keys.includes(this.highlightedSeries)) {
      this.highlightedSeries = null;
    }
  }

  toggleElementVisibility(elementName: string): void {
    const keys = this.normalizedSeries
      .filter((s) => VISIBLE_LANES.has(s.lane) && s.elementName === elementName)
      .map((s) => s.key);
    if (keys.length === 0) {
      return;
    }
    const allHidden = keys.every((key) => this.hiddenSeriesKeys.has(key));
    if (allHidden) {
      for (const key of keys) {
        this.hiddenSeriesKeys.delete(key);
        this.forcedVisibleSeriesKeys.add(key);
      }
    } else {
      for (const key of keys) {
        this.hiddenSeriesKeys.add(key);
        this.forcedVisibleSeriesKeys.delete(key);
        if (this.highlightedSeries === key) {
          this.highlightedSeries = null;
        }
      }
    }
    this.visibilityRevision += 1;
    this.recomputePowerBounds();
  }

  togglePowerDisplayMode(): void {
    this.powerDisplayModeOverride = this.powerDisplayMode === "opposed" ? "overlay" : "opposed";
    this.recomputePowerBounds();
  }

  toggleTooltipVisibility(): void {
    this.tooltipVisible = !this.tooltipVisible;
  }

  setHorizon(durationMs: HorizonOption): void {
    if (this.horizonDurationMs === durationMs) {
      return;
    }
    const from = this.xDomain;
    this.horizonDurationMs = durationMs;
    this.horizonRevision += 1;
    const to = this.selectedXDomain;
    this.startHorizonAnimation(from, to);
    this.recomputePowerBounds();
  }

  // --- Computed: config-derived ---

  get powerDisplayMode(): PowerDisplayMode {
    return this.powerDisplayModeOverride ?? this.config.power_display_mode ?? "opposed";
  }

  get locale(): string {
    return this.hass?.language ?? this.hass?.locale?.language ?? "en";
  }

  // --- Computed: layout ---

  get margins(): ChartMargins {
    const compact = this.width < 420;
    const left = between(compact ? 56 : 72, this.width * 0.075, 92);
    const right = between(compact ? 64 : 84, this.width * 0.085, 112);
    return {
      top: compact ? 20 : 26,
      right: Math.round(right),
      bottom: compact ? 42 : 50,
      left: Math.round(left),
    };
  }

  get plotTop(): number {
    return this.margins.top;
  }

  get plotBottom(): number {
    return this.height - this.margins.bottom;
  }

  // --- Computed: series filtering ---

  get normalizedSeries(): ForecastSeries[] {
    return this.normalizedSeriesCache;
  }

  get pairedPowerPotentialKeys(): Set<string> {
    const utilizationPairs = new Set(
      this.normalizedSeries
        .filter((series) => series.lane === "power" && series.sourceRole === "output")
        .map((series) => powerPairKey(series))
    );
    return new Set(
      this.normalizedSeries
        .filter((series) => isPowerPotentialSeries(series) && utilizationPairs.has(powerPairKey(series)))
        .map((series) => series.key)
    );
  }

  get legendSeries(): ForecastSeries[] {
    const pairedPotentials = this.pairedPowerPotentialKeys;
    return this.normalizedSeries.filter((s) => VISIBLE_LANES.has(s.lane) && !pairedPotentials.has(s.key));
  }

  get visibleSeries(): ForecastSeries[] {
    return this.normalizedSeries.filter((s) => VISIBLE_LANES.has(s.lane) && !this.hiddenSeriesKeys.has(s.key));
  }

  get powerSeries(): ForecastSeries[] {
    return this.visibleSeries.filter((s) => s.lane === "power" && s.sourceRole !== "limit");
  }

  get orderedPowerSeries(): ForecastSeries[] {
    return [...this.powerSeries].sort((a, b) => {
      // Primary sort: optimizer priority from the backend determines stack order.
      const aPriority = a.priority ?? Number.POSITIVE_INFINITY;
      const bPriority = b.priority ?? Number.POSITIVE_INFINITY;
      if (aPriority !== bPriority) return aPriority - bPriority;
      return a.label.localeCompare(b.label);
    });
  }

  get priceSeries(): ForecastSeries[] {
    return this.visibleSeries.filter((s) => s.lane === "price");
  }

  get socSeries(): ForecastSeries[] {
    return this.visibleSeries.filter((s) => s.lane === "soc");
  }

  get hasData(): boolean {
    return this.legendSeries.length > 0;
  }

  get hasPlottedData(): boolean {
    return this.visibleSeries.length > 0;
  }

  // --- Computed: focus/highlight ---

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

  get focusedLegendSeriesKeys(): Set<string> {
    if (this.highlightedSeriesGroupKeys.size > 0) {
      return new Set(this.highlightedSeriesGroupKeys);
    }
    if (this.highlightedSeries !== null) {
      return new Set([this.highlightedSeries]);
    }
    return this.focusedElementSeriesKeys;
  }

  // --- Computed: x-axis / animation ---

  get fullXDomain(): Domain {
    if (!this.hasPlottedData) {
      const now = Date.now();
      return { min: now, max: now + 60_000, step: 60_000 };
    }
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    let step = Number.POSITIVE_INFINITY;
    for (const item of this.visibleSeries) {
      if (item.times.length < 2) continue;
      const first = item.times[0];
      const second = item.times[1];
      const last = item.times[item.times.length - 1];
      if (first === undefined || second === undefined || last === undefined) continue;
      min = Math.min(min, first);
      max = Math.max(max, last);
      step = Math.min(step, Math.max(1, second - first));
    }
    if (!Number.isFinite(min) || !Number.isFinite(max) || !Number.isFinite(step)) {
      const now = Date.now();
      return { min: now, max: now + 60_000, step: 60_000 };
    }
    return { min, max, step };
  }

  get selectedXDomain(): Domain {
    const domain = this.fullXDomain;
    if (this.horizonDurationMs === null) {
      return domain;
    }
    const horizonMax = domain.min + this.horizonDurationMs;
    return {
      min: domain.min,
      max: Math.min(domain.max, horizonMax),
      step: domain.step,
    };
  }

  get xDomain(): Domain {
    const animation = this.horizonAnimation;
    if (animation === null) {
      return this.selectedXDomain;
    }
    const elapsed = this.horizonAnimationNowMs - animation.startMs;
    const progress = clamp(elapsed / HORIZON_ANIMATION_MS, 0, 1);
    const eased = 1 - (1 - progress) ** 3;
    return {
      min: animation.from.min + (animation.to.min - animation.from.min) * eased,
      max: animation.from.max + (animation.to.max - animation.from.max) * eased,
      step: animation.to.step,
    };
  }

  get horizonOptions(): HorizonOption[] {
    const fullDuration = this.fullXDomain.max - this.fullXDomain.min;
    const options = BASE_HORIZON_OPTIONS_MS.filter((duration) => duration < fullDuration);
    const maxWholeDays = Math.max(0, Math.floor(fullDuration / DAY_MS));
    for (let day = 1; day < maxWholeDays; day += 1) {
      const duration = day * DAY_MS;
      if (duration > (options[options.length - 1] ?? 0) && duration < fullDuration) {
        options.push(duration);
      }
    }
    return [...options, null];
  }

  /** Cached x-scale function reused by plotPaths and hover mapping. */
  get cachedXScale(): (time: number) => number {
    const { min, max } = this.xDomain;
    const innerWidth = this.width - this.margins.left - this.margins.right;
    const left = this.margins.left;
    return (time: number) => linearScale(time, min, max, left, left + innerWidth);
  }

  xScale(time: number): number {
    return this.cachedXScale(time);
  }

  // --- Computed: y-axis bounds ---

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

  get powerBounds(): LaneBounds {
    return this.powerBoundsCache;
  }

  get priceBounds(): LaneBounds {
    return this._bounds(this.priceSeries, { min: 0, max: 1 });
  }

  get socBounds(): LaneBounds {
    return { min: 0, max: 100 };
  }

  // --- Computed: y-scale functions ---

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

  // --- Computed: hover ---

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

  get hoverTimeMs(): number | null {
    if (this.pointerX === null) {
      return null;
    }
    const x = clamp(this.pointerX, this.margins.left, this.width - this.margins.right);
    const { min, max } = this.xDomain;
    const innerWidth = this.width - this.margins.left - this.margins.right;
    const ratio = innerWidth > 0 ? (x - this.margins.left) / innerWidth : 0;
    return min + ratio * (max - min);
  }

  get panelTimeMs(): number {
    return this.hoverTimeMs ?? this.xDomain.min;
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
    return computeHoverIndices(this.visibleSeries, time);
  }

  get panelIndices(): Map<string, number> {
    return computeHoverIndices(this.visibleSeries, this.panelTimeMs);
  }

  get sharedTimeline(): Float64Array | null {
    return sharedTimeline(this.visibleSeries);
  }

  // --- Computed: SVG paths ---

  private plotPathsCacheKey(): string {
    const { min, max } = this.xDomain;
    return [
      this.seriesDataRevision,
      this.visibilityRevision,
      this.powerDisplayMode,
      this.width,
      this.height,
      this.horizonDurationMs,
      min,
      max,
      this.horizonAnimationNowMs,
      this.powerBoundsCache.min,
      this.powerBoundsCache.max,
    ].join("\0");
  }

  get plotPaths(): PlotPaths {
    const key = this.plotPathsCacheKey();
    if (this.plotPathsSnapshot !== null && this.plotPathsSnapshotKey === key) {
      return this.plotPathsSnapshot;
    }
    const xScale = this.cachedXScale;
    const snapshot: PlotPaths = {
      powerShapes: computePowerShapes(
        this.orderedPowerSeries,
        this.powerBounds,
        this.powerDisplayMode,
        this.plotTop,
        this.plotBottom,
        xScale
      ),
      pricePaths: computePricePaths(
        this.priceSeries,
        this.powerBounds,
        this.priceBounds,
        this.plotTop,
        this.plotBottom,
        xScale
      ),
      socPaths: computeSocPaths(
        this.socSeries,
        this.powerBounds,
        this.socBounds,
        this.plotTop,
        this.plotBottom,
        xScale
      ),
    };
    this.plotPathsSnapshotKey = key;
    this.plotPathsSnapshot = snapshot;
    return snapshot;
  }

  get powerShapes(): PowerShape[] {
    return this.plotPaths.powerShapes;
  }

  get hoveredPowerSeriesKeys(): Set<string> {
    if (!this.isHoverInPlot || this.pointerY === null) {
      return new Set();
    }
    const time = this.hoverTimeMs;
    if (time === null) {
      return new Set();
    }
    return computeHoveredPowerKeys(
      this.orderedPowerSeries,
      this.hoverIndices,
      this.powerDisplayMode,
      this.powerBounds,
      this.plotTop,
      this.plotBottom,
      this.pointerY
    );
  }

  get pricePaths(): LineSvgPath[] {
    return this.plotPaths.pricePaths;
  }

  get socPaths(): LineSvgPath[] {
    return this.plotPaths.socPaths;
  }

  // --- Computed: tooltip ---

  private powerValueForDisplayBound(series: ForecastSeries, value: number): number {
    return powerValueForDisplay(series, value, this.powerDisplayMode);
  }

  get tooltipRows(): Array<{
    key: string;
    possibleKey?: string;
    label: string;
    value: number;
    possibleValue?: number;
    unit: string;
    color: string;
    lane: TooltipSectionId;
  }> {
    return buildTooltipRows(
      this.visibleSeries,
      this.panelIndices,
      this.normalizedSeries,
      computeHoverIndices(this.normalizedSeries, this.panelTimeMs),
      (series, value) => this.powerValueForDisplayBound(series, value)
    );
  }

  get tooltipEmphasisKeys(): Set<string> {
    const keys = new Set<string>();
    for (const key of this.hoveredPowerSeriesKeys) {
      keys.add(key);
    }
    for (const key of this.highlightedSeriesGroupKeys) {
      keys.add(key);
    }
    if (this.highlightedSeries !== null) {
      keys.add(this.highlightedSeries);
    }
    return keys;
  }

  // --- Internal ---

  private visibilityGroupKeys(key: string): string[] {
    const series = this.normalizedSeries.find((item) => item.key === key);
    if (series?.lane !== "power" || series.sourceRole !== "output") {
      return [key];
    }
    const pairKey = powerPairKey(series);
    return this.normalizedSeries
      .filter((item) => item.key === key || (isPowerPotentialSeries(item) && powerPairKey(item) === pairKey))
      .map((item) => item.key);
  }

  private applyDefaultHiddenSeries(): void {
    let hiddenChanged = false;
    const directionalByElement = new Map<string, { hasProd: boolean; hasCons: boolean }>();
    for (const series of this.normalizedSeries) {
      if (series.lane !== "power") continue;
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
      if (this.forcedVisibleSeriesKeys.has(series.key)) {
        continue;
      }

      // Hide all policy element series by default.
      if (series.elementType === "policy") {
        const before = this.hiddenSeriesKeys.size;
        this.hiddenSeriesKeys.add(series.key);
        hiddenChanged ||= this.hiddenSeriesKeys.size !== before;
        continue;
      }

      if (series.lane !== "power") continue;
      const isGrid = series.elementName.toLowerCase().includes("grid");
      const category = classifyPowerSeries(series);
      const output = series.outputName.toLowerCase();
      const pair = directionalByElement.get(series.elementName);

      const hideByDefault =
        (isGrid && category.subgroup === "potential") ||
        ((output.includes("active") || output.includes("balance")) &&
          pair !== undefined &&
          pair.hasProd &&
          pair.hasCons);
      if (hideByDefault) {
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
    this.seriesDataRevision += 1;

    const seriesKeys = new Set(nextSeries.map((s) => s.key));
    this.hiddenSeriesKeys = new Set([...this.hiddenSeriesKeys].filter((key) => seriesKeys.has(key)));
    this.forcedVisibleSeriesKeys = new Set([...this.forcedVisibleSeriesKeys].filter((key) => seriesKeys.has(key)));
    if (this.highlightedSeries !== null && !seriesKeys.has(this.highlightedSeries)) {
      this.highlightedSeries = null;
    }
    this.highlightedSeriesGroupKeys = new Set(
      [...this.highlightedSeriesGroupKeys].filter((key) => seriesKeys.has(key))
    );
    if (this.hoveredLegendElement !== null) {
      const hasHoveredElement = nextSeries.some((s) => s.elementName === this.hoveredLegendElement);
      if (!hasHoveredElement) {
        this.hoveredLegendElement = null;
      }
    }

    this.applyDefaultHiddenSeries();
    this.recomputePowerBounds();
  }

  private startHorizonAnimation(from: Domain, to: Domain): void {
    if (this.horizonAnimationFrame !== 0) {
      cancelAnimationFrame(this.horizonAnimationFrame);
      this.horizonAnimationFrame = 0;
    }
    const startMs = globalThis.performance.now();
    this.horizonAnimation = { from, to, startMs };
    this.horizonAnimationNowMs = startMs;
    const tick = (nowMs: number): void => {
      this.horizonAnimationNowMs = nowMs;
      if (nowMs - startMs >= HORIZON_ANIMATION_MS) {
        this.horizonAnimation = null;
        this.horizonAnimationFrame = 0;
        return;
      }
      this.horizonAnimationFrame = requestAnimationFrame(tick);
    };
    this.horizonAnimationFrame = requestAnimationFrame(tick);
  }

  private recomputePowerBounds(): void {
    this.powerBoundsCache = calculatePowerBounds(this.orderedPowerSeries, this.powerDisplayMode);
  }
}
