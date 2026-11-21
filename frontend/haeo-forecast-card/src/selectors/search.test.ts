import { describe, expect, it } from "vitest";

import { describeEntity, filterOptions, offeredEntityIds, parseConstant } from "./search";
import type { InputSelectorConfig, SelectorHass } from "./types";

const hass: SelectorHass = {
  localize: () => "",
  states: {
    "sensor.b": {
      entity_id: "sensor.b",
      state: "2.5",
      attributes: { friendly_name: "Battery power", unit_of_measurement: "kW" },
    },
    "sensor.a": { entity_id: "sensor.a", state: "unavailable", attributes: { friendly_name: "Solar power" } },
    "sensor.c": { entity_id: "sensor.c", state: "on", attributes: {} },
    "light.d": { entity_id: "light.d", state: "on", attributes: { friendly_name: "Desk lamp" } },
  },
};

const config: InputSelectorConfig = {
  kinds: ["entity", "constant", "none"],
  value_type: "number",
  domains: ["sensor"],
  entities: ["sensor.a", "sensor.b", "sensor.c"],
  min: 0,
  max: 100,
};

describe("describeEntity", () => {
  it("shows the friendly name and the state with its unit", () => {
    expect(describeEntity(hass, "sensor.b")).toEqual({
      entityId: "sensor.b",
      name: "Battery power",
      current: "2.5 kW",
    });
  });

  it("falls back to the entity ID and hides an unavailable state", () => {
    expect(describeEntity(hass, "sensor.a").current).toBe("");
    expect(describeEntity(hass, "sensor.c").name).toBe("sensor.c");
    expect(describeEntity(null, "sensor.gone")).toEqual({ entityId: "sensor.gone", name: "sensor.gone", current: "" });
  });
});

describe("offeredEntityIds", () => {
  it("lists a field's own entities sorted by name", () => {
    expect(offeredEntityIds(hass, config)).toEqual(["sensor.b", "sensor.c", "sensor.a"]);
  });

  it("lists every entity in the field's domains when it names none", () => {
    const byDomain: InputSelectorConfig = { kinds: config.kinds, value_type: "number", domains: ["sensor", "light"] };
    expect(offeredEntityIds(hass, byDomain)).toEqual(["sensor.b", "light.d", "sensor.c", "sensor.a"]);
  });
});

describe("filterOptions", () => {
  const options = offeredEntityIds(hass, config).map((entityId) => describeEntity(hass, entityId));

  it("keeps options matching every word in the name or entity ID", () => {
    expect(filterOptions(options, "power battery").map((option) => option.entityId)).toEqual(["sensor.b"]);
    expect(filterOptions(options, "SENSOR.C").map((option) => option.entityId)).toEqual(["sensor.c"]);
  });

  it("keeps everything for an empty query", () => {
    expect(filterOptions(options, "  ")).toHaveLength(3);
  });
});

describe("parseConstant", () => {
  it.each([
    ["5", 5],
    [" 0.8 ", 0.8],
    ["100", 100],
  ])("reads %j as %d", (text, value) => {
    expect(parseConstant(text, config)).toBe(value);
  });

  it.each(["", "abc", "101", "-1", "Infinity"])("rejects %j", (text) => {
    expect(parseConstant(text, config)).toBeNull();
  });

  it("rejects numbers for fields without a number constant", () => {
    expect(parseConstant("5", { ...config, kinds: ["entity"] })).toBeNull();
    expect(parseConstant("5", { ...config, value_type: "boolean" })).toBeNull();
  });
});
