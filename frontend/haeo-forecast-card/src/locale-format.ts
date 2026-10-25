/**
 * Date, time and number formatting that follows the Home Assistant user profile.
 *
 * The profile's localization settings choose the time format (`12`, `24`,
 * `system` or `language`), the date format (`DMY`, `MDY`, `YMD`, `system` or
 * `language`), the number format (`language`, `system`, `comma_decimal`,
 * `decimal_comma`, `space_comma` or `none`) and the time zone (`local` or
 * `server`). `system` follows the browser and `language` the chosen language.
 */

/** The localization settings Home Assistant keeps in the user profile. */
export interface HassLocaleSettings {
  language?: string;
  time_format?: string;
  date_format?: string;
  number_format?: string;
  time_zone?: string;
}

/** How the card formats dates, times and numbers for the current user. */
export interface DisplayFormat {
  language: string;
  hour12: boolean | undefined;
  dateFormat: string | undefined;
  numberLocale: string | string[] | undefined;
  useGrouping: boolean;
  timeZone: string | undefined;
}

const dateTimeFormatters = new Map<string, Intl.DateTimeFormat>();
const numberFormatters = new Map<string, Intl.NumberFormat>();

/** Return a cached Intl.DateTimeFormat, because the tooltip formats on every pointer move. */
function dateTimeFormatter(
  locale: string | string[] | undefined,
  options: Intl.DateTimeFormatOptions
): Intl.DateTimeFormat {
  const key = JSON.stringify([locale, options]);
  let formatter = dateTimeFormatters.get(key);
  if (formatter === undefined) {
    formatter = new Intl.DateTimeFormat(locale, options);
    dateTimeFormatters.set(key, formatter);
  }
  return formatter;
}

/** Return a cached Intl.NumberFormat. */
function numberFormatter(locale: string | string[] | undefined, options: Intl.NumberFormatOptions): Intl.NumberFormat {
  const key = JSON.stringify([locale, options]);
  let formatter = numberFormatters.get(key);
  if (formatter === undefined) {
    formatter = new Intl.NumberFormat(locale, options);
    numberFormatters.set(key, formatter);
  }
  return formatter;
}

/** Return whether times use a 12-hour clock, or undefined to leave it to the language. */
export function hour12ForTimeFormat(timeFormat: string | undefined): boolean | undefined {
  switch (timeFormat) {
    case "12":
      return true;
    case "24":
      return false;
    case "system": {
      const { hourCycle } = new Intl.DateTimeFormat(undefined, { hour: "numeric" }).resolvedOptions();
      return hourCycle === "h11" || hourCycle === "h12";
    }
    default:
      return undefined;
  }
}

/** Return the locale whose separators a number format uses, as Home Assistant maps them. */
function numberLocaleFor(numberFormat: string | undefined, language: string): string | string[] | undefined {
  switch (numberFormat) {
    case "comma_decimal":
      return ["en-US", "en"];
    case "decimal_comma":
      return ["de", "es", "it"];
    case "space_comma":
      return ["fr", "sv", "cs"];
    case "none":
      return "en-US";
    case "system":
      return undefined;
    default:
      return language || undefined;
  }
}

/** Build the display format from the profile settings and the server's time zone. */
export function displayFormat(
  language: string,
  settings: HassLocaleSettings | undefined,
  serverTimeZone: string | undefined
): DisplayFormat {
  return {
    language,
    hour12: hour12ForTimeFormat(settings?.time_format),
    dateFormat: settings?.date_format,
    numberLocale: numberLocaleFor(settings?.number_format, language),
    useGrouping: settings?.number_format !== "none",
    timeZone: settings?.time_zone === "server" ? serverTimeZone : undefined,
  };
}

/** Return a number with a fixed count of decimals, such as 1.234,50 for decimal_comma. */
export function formatNumber(value: number, format: DisplayFormat, fractionDigits: number): string {
  return numberFormatter(format.numberLocale, {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
    useGrouping: format.useGrouping,
  }).format(value);
}

/** Return a time of day such as 21:02, or 9:02 PM on a 12-hour clock. */
export function formatTime(ms: number, format: DisplayFormat, withSeconds = false): string {
  return dateTimeFormatter(format.language || undefined, {
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
    hour12: format.hour12,
    timeZone: format.timeZone,
  }).format(ms);
}

/** Return a numeric date such as 25/10/2026, ordered by the profile's date format. */
export function formatDateNumeric(ms: number, format: DisplayFormat): string {
  const locale = format.dateFormat === "system" ? undefined : format.language || undefined;
  const formatter = dateTimeFormatter(locale, {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    timeZone: format.timeZone,
  });
  const order = {
    DMY: ["day", "month", "year"],
    MDY: ["month", "day", "year"],
    YMD: ["year", "month", "day"],
  } as const;
  if (format.dateFormat !== "DMY" && format.dateFormat !== "MDY" && format.dateFormat !== "YMD") {
    return formatter.format(ms);
  }
  const parts = formatter.formatToParts(ms);
  const part = (type: Intl.DateTimeFormatPartTypes): string => parts.find((p) => p.type === type)?.value ?? "";
  // The language's separator between the numbers, such as "/" or "-"
  const separator = parts.find((p) => p.type === "literal")?.value ?? "/";
  return order[format.dateFormat].map(part).join(separator);
}

/** Return a date and time such as 25/10/2026, 21:02:11 for a tooltip. */
export function formatDateTime(ms: number, format: DisplayFormat): string {
  return `${formatDateNumeric(ms, format)}, ${formatTime(ms, format, true)}`;
}

/**
 * Return how far the wall clock of a time zone is ahead of UTC at a moment, in milliseconds.
 *
 * An undefined time zone is the browser's own, so ticks line up with the clock the user reads.
 */
export function wallClockOffsetMs(ms: number, timeZone: string | undefined): number {
  if (timeZone === undefined) {
    return -new Date(ms).getTimezoneOffset() * 60_000;
  }
  const parts = dateTimeFormatter("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
  }).formatToParts(ms);
  const value = (type: Intl.DateTimeFormatPartTypes): number => Number(parts.find((p) => p.type === type)?.value);
  const wallClockAsUtc = Date.UTC(
    value("year"),
    value("month") - 1,
    value("day"),
    value("hour"),
    value("minute"),
    value("second")
  );
  return wallClockAsUtc - Math.floor(ms / 1000) * 1000;
}
