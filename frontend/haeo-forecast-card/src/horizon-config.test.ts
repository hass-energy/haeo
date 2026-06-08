import { describe, expect, it } from "vitest";

import { clampHorizonToOptions, horizonPresetToDuration } from "./horizon-config";

const HOUR_MS = 3_600_000;

describe("horizonPresetToDuration", () => {
  it("maps presets to milliseconds", () => {
    expect(horizonPresetToDuration("full")).toBeNull();
    expect(horizonPresetToDuration(undefined)).toBeNull();
    expect(horizonPresetToDuration("4h")).toBe(4 * HOUR_MS);
  });
});

describe("clampHorizonToOptions", () => {
  const options = [HOUR_MS, 2 * HOUR_MS, 4 * HOUR_MS, null] as const;

  it("keeps valid configured horizons", () => {
    expect(clampHorizonToOptions(4 * HOUR_MS, options)).toBe(4 * HOUR_MS);
  });

  it("uses the nearest shorter option when the forecast is shorter", () => {
    expect(clampHorizonToOptions(8 * HOUR_MS, options)).toBe(4 * HOUR_MS);
  });

  it("falls back to full forecast when nothing fits", () => {
    expect(clampHorizonToOptions(30 * 60_000, [HOUR_MS, null])).toBeNull();
  });
});
