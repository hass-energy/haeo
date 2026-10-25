import { afterEach, describe, expect, it, vi } from "vitest";

import type * as LocaleFormat from "./locale-format";
import {
  displayFormat,
  formatDateNumeric,
  formatDateTime,
  formatNumber,
  formatTime,
  hour12ForTimeFormat,
  wallClockOffsetMs,
  type HassLocaleSettings,
} from "./locale-format";

// 25 October 2026, 21:02:11 local time
const MS = new Date(2026, 9, 25, 21, 2, 11).getTime();

const format = (settings: HassLocaleSettings, language = "en", serverTimeZone?: string) =>
  displayFormat(language, settings, serverTimeZone);

const { DateTimeFormat, NumberFormat } = Intl;

/** Load the module as if the browser's own locale were the given one. */
async function withBrowserLocale(browserLocale: string): Promise<typeof LocaleFormat> {
  vi.spyOn(Intl, "DateTimeFormat").mockImplementation(
    (locales, options) => new DateTimeFormat(locales ?? browserLocale, options)
  );
  vi.spyOn(Intl, "NumberFormat").mockImplementation(
    (locales, options) => new NumberFormat(locales ?? browserLocale, options)
  );
  vi.resetModules();
  return import("./locale-format");
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("hour12ForTimeFormat", () => {
  it("uses a 12-hour clock for the 12 format", () => {
    expect(hour12ForTimeFormat("12")).toBe(true);
  });

  it("uses a 24-hour clock for the 24 format", () => {
    expect(hour12ForTimeFormat("24")).toBe(false);
  });

  it.each([
    ["en-US", true],
    ["de", false],
  ])("follows the clock of a %s browser for the system format", async (browserLocale, expected) => {
    const { hour12ForTimeFormat } = await withBrowserLocale(browserLocale);
    expect(hour12ForTimeFormat("system")).toBe(expected);
  });

  it.each(["language", undefined])("leaves the %s format to the language", (timeFormat) => {
    expect(hour12ForTimeFormat(timeFormat)).toBeUndefined();
  });
});

describe("formatTime", () => {
  it.each([
    ["24", "21:02"],
    ["12", "9:02 PM"],
  ])("follows the %s time format", (timeFormat, expected) => {
    expect(formatTime(MS, format({ time_format: timeFormat }))).toBe(expected);
  });

  it("pads the hour on a 24-hour clock", () => {
    const morning = new Date(2026, 9, 25, 9, 2).getTime();
    expect(formatTime(morning, format({ time_format: "24" }))).toBe("09:02");
  });

  it("falls back to the browser's time zone when the server's is unknown", () => {
    const shown = format({ time_format: "24", time_zone: "server" }, "en", "Not/A_Zone");
    expect(shown.timeZone).toBeUndefined();
    expect(formatTime(MS, shown)).toBe("21:02");
  });

  it("shows the server's time zone when the profile asks for it", () => {
    const utc = Date.UTC(2026, 9, 25, 12, 0, 0);
    const shown = format({ time_format: "24", time_zone: "server" }, "en", "Asia/Tokyo");
    expect(formatTime(utc, shown)).toBe("21:00");
  });

  it("ignores the server's time zone for the local setting", () => {
    expect(format({ time_zone: "local" }, "en", "Asia/Tokyo").timeZone).toBeUndefined();
  });
});

describe("formatDateNumeric", () => {
  it.each([
    ["DMY", "25/10/2026"],
    ["MDY", "10/25/2026"],
    ["YMD", "2026/10/25"],
  ])("orders the date for the %s format", (dateFormat, expected) => {
    expect(formatDateNumeric(MS, format({ date_format: dateFormat }))).toBe(expected);
  });

  it("keeps the language's own separator", () => {
    expect(formatDateNumeric(MS, format({ date_format: "YMD" }, "nl"))).toBe("2026-10-25");
  });

  it("uses the language's own order for the language format", () => {
    expect(formatDateNumeric(MS, format({ date_format: "language" }))).toBe("10/25/2026");
  });

  it.each([
    ["hu", "DMY", "25. 10. 2026."],
    ["hu", "YMD", "2026. 10. 25."],
    ["bg", "DMY", "25.10.2026 г."],
    ["bg", "MDY", "10.25.2026 г."],
    ["bg", "YMD", "2026.10.25"],
  ])("keeps the trailing text of %s for the %s format", (language, dateFormat, expected) => {
    // Bulgarian separates " г." with a narrow no-break space
    expect(formatDateNumeric(MS, format({ date_format: dateFormat }, language)).replace(/\s/gu, " ")).toBe(expected);
  });

  it("uses the browser's own format for the system format", async () => {
    const { displayFormat, formatDateNumeric } = await withBrowserLocale("de");
    expect(formatDateNumeric(MS, displayFormat("nl", { date_format: "system" }, undefined))).toBe("25.10.2026");
  });
});

describe("formatDateTime", () => {
  it("combines the profile's date format and clock", () => {
    expect(formatDateTime(MS, format({ date_format: "DMY", time_format: "24" }))).toBe("25/10/2026, 21:02:11");
  });

  it("shows the day period on a 12-hour clock", () => {
    expect(formatDateTime(MS, format({ date_format: "MDY", time_format: "12" }))).toBe("10/25/2026, 9:02:11 PM");
  });

  it.each([
    ["en", "10/25/2026, 9:02:11 PM"],
    ["hu", "2026. 10. 25. 21:02:11"],
    ["ja", "2026/10/25 21:02:11"],
  ])("joins the date and time the way %s does for the language format", (language, expected) => {
    expect(formatDateTime(MS, format({ date_format: "language" }, language))).toBe(expected);
  });

  it("applies the profile's clock to the language format", () => {
    expect(formatDateTime(MS, format({ date_format: "language", time_format: "24" }))).toBe("10/25/2026, 21:02:11");
  });

  it("uses the browser's own date and time for the system format", async () => {
    const { displayFormat, formatDateTime } = await withBrowserLocale("de");
    expect(formatDateTime(MS, displayFormat("en", { date_format: "system" }, undefined))).toBe("25.10.2026, 21:02:11");
  });
});

describe("formatNumber", () => {
  it.each([
    ["comma_decimal", "1,234.50"],
    ["decimal_comma", "1.234,50"],
    ["none", "1234.50"],
    ["language", "1,234.50"],
  ])("uses the separators of the %s number format", (numberFormat, expected) => {
    expect(formatNumber(1234.5, format({ number_format: numberFormat }), 2)).toBe(expected);
  });

  it("groups with a space for the space_comma number format", () => {
    expect(formatNumber(1234.5, format({ number_format: "space_comma" }), 2).replace(/\s/gu, " ")).toBe("1 234,50");
  });

  it("uses the language's separators for the language number format", () => {
    expect(formatNumber(0.14, format({ number_format: "language" }, "nl"), 2)).toBe("0,14");
  });

  it("uses the browser's separators for the system number format", async () => {
    const { displayFormat, formatNumber } = await withBrowserLocale("de");
    expect(formatNumber(1234.5, displayFormat("en", { number_format: "system" }, undefined), 2)).toBe("1.234,50");
  });
});

describe("wallClockOffsetMs", () => {
  it("measures a named time zone's offset from UTC", () => {
    expect(wallClockOffsetMs(Date.UTC(2026, 0, 15, 12), "Asia/Tokyo")).toBe(9 * 3_600_000);
  });

  it("follows daylight saving time", () => {
    expect(wallClockOffsetMs(Date.UTC(2026, 6, 15, 12), "Europe/Amsterdam")).toBe(2 * 3_600_000);
    expect(wallClockOffsetMs(Date.UTC(2026, 11, 15, 12), "Europe/Amsterdam")).toBe(1 * 3_600_000);
  });

  it("uses the browser's offset without a time zone", () => {
    expect(wallClockOffsetMs(MS, undefined)).toBe(-new Date(MS).getTimezoneOffset() * 60_000);
  });
});
