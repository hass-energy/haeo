import { describe, expect, it } from "vitest";

import { buildHubConfigForm } from "./config-form";

describe("config-form", () => {
  it("requires a HAEO hub in the built-in editor schema", () => {
    const form = buildHubConfigForm();
    const hubField = form.schema.find((field) => field.name === "hub_entry_id");
    expect(hubField?.required).toBe(true);
    expect(hubField?.selector).toEqual({ config_entry: { integration: "haeo" } });
    expect(form.computeLabel({ name: "hub_entry_id" })).toBe("HAEO hub");
    expect(form.computeHelper({ name: "hub_entry_id" })).toBe("Select the HAEO system this card should display.");
  });

  it("labels the title field and ignores unknown schema names", () => {
    const form = buildHubConfigForm();
    expect(form.computeLabel({ name: "title" })).toBe("Title");
    expect(form.computeLabel({ name: "unknown" })).toBeUndefined();
    expect(form.computeHelper({ name: "title" })).toBeUndefined();
  });

  it("exposes editor defaults for power mode, horizon, and tooltip visibility", () => {
    const form = buildHubConfigForm();
    expect(form.schema.find((field) => field.name === "power_display_mode")?.default).toBe("opposed");
    expect(form.schema.find((field) => field.name === "default_horizon")?.default).toBe("full");
    expect(form.schema.find((field) => field.name === "tooltip_visible")?.default).toBe(true);
    expect(form.computeLabel({ name: "power_display_mode" })).toBe("Power display mode");
    expect(form.computeLabel({ name: "default_horizon" })).toBe("Default horizon");
    expect(form.computeLabel({ name: "tooltip_visible" })).toBe("Show information panel");
    expect(form.computeHelper({ name: "power_display_mode" })).toContain("separate axes");
    expect(form.computeHelper({ name: "default_horizon" })).toContain("horizon slider");
    expect(form.computeHelper({ name: "tooltip_visible" })).toContain("information panel");
  });
});
