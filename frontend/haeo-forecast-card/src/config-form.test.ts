import { describe, expect, it } from "vitest";

import { buildHubConfigForm } from "./config-form";

describe("config-form", () => {
  it("requires a HAEO hub in the built-in editor schema", () => {
    const form = buildHubConfigForm();
    const hubField = form.schema.find((field) => field.name === "hub_entry_id");
    expect(hubField?.required).toBe(true);
    expect(hubField?.selector).toEqual({ config_entry: { integration: "haeo" } });
    expect(form.computeLabel({ name: "hub_entry_id" })).toBe("HAEO hub");
  });
});
