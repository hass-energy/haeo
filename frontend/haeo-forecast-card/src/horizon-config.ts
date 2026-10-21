const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

export type HorizonOption = number | null;

export const DEFAULT_HORIZON_PRESETS = ["full", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "2d", "3d"] as const;

export type DefaultHorizonPreset = (typeof DEFAULT_HORIZON_PRESETS)[number];

const PRESET_MS: Record<Exclude<DefaultHorizonPreset, "full">, number> = {
  "15m": 15 * MINUTE_MS,
  "30m": 30 * MINUTE_MS,
  "1h": HOUR_MS,
  "2h": 2 * HOUR_MS,
  "4h": 4 * HOUR_MS,
  "8h": 8 * HOUR_MS,
  "12h": 12 * HOUR_MS,
  "1d": DAY_MS,
  "2d": 2 * DAY_MS,
  "3d": 3 * DAY_MS,
};

export function horizonPresetToDuration(preset: DefaultHorizonPreset | undefined): HorizonOption {
  if (preset === undefined || preset === "full") {
    return null;
  }
  return PRESET_MS[preset];
}

export function clampHorizonToOptions(requested: HorizonOption, options: readonly HorizonOption[]): HorizonOption {
  if (options.length === 0) {
    return requested;
  }
  if (requested === null) {
    return options.includes(null) ? null : (options[options.length - 1] ?? null);
  }
  if (options.includes(requested)) {
    return requested;
  }
  const numericOptions = options.filter((option): option is number => option !== null);
  const eligible = numericOptions.filter((duration) => duration <= requested);
  if (eligible.length > 0) {
    return eligible[eligible.length - 1]!;
  }
  return null;
}
