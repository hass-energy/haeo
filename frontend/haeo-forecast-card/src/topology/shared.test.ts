import { describe, expect, it } from "vitest";

import { reserveRoles, reserveTooltipLines } from "./shared";

describe("reserveRoles", () => {
  it("records which reserves each node holds and counts toward", () => {
    const roles = reserveRoles([
      { name: "Backup", elements: ["House", "Solar"], storage: ["Battery"] },
      { name: "Essentials", elements: ["House"], storage: ["Battery"] },
    ]);

    expect(roles.get("Battery")).toEqual({ holds: ["Backup", "Essentials"], covers: [] });
    expect(roles.get("House")).toEqual({ holds: [], covers: ["Backup", "Essentials"] });
    expect(reserveTooltipLines(roles.get("Battery"))).toEqual(["Holds reserve: Backup, Essentials"]);
    expect(reserveTooltipLines(roles.get("Solar"))).toEqual(["Counted in reserve: Backup"]);
    expect(reserveTooltipLines(roles.get("Grid"))).toEqual([]);
  });

  it("returns no roles without reserves", () => {
    expect(reserveRoles(undefined).size).toBe(0);
  });
});
