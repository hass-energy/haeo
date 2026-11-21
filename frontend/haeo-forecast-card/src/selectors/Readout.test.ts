import { describe, expect, it } from "vitest";

import { shortNumber } from "./Readout";

describe("shortNumber", () => {
  it.each([
    [0.501, "0.501"],
    [12.345, "12.3"],
    [1234, "1.23K"],
    [0, "0"],
    [0.000123, "1.2e-4"],
  ])("shortens %s to %s", (value, expected) => {
    expect(shortNumber(value, "en")).toBe(expected);
  });

  it("formats in the user's language", () => {
    expect(shortNumber(0.5, "de")).toBe("0,5");
  });
});
