import { describe, expect, it } from "vitest";

import { reserveMarkers, reserveRoles, reserveTooltipLines } from "./shared";

describe("reserveRoles", () => {
  const roles = reserveRoles([
    { name: "Backup", kind: "reserve", elements: ["House", "Solar"], storage: ["Battery"] },
    { name: "Essentials", kind: "reserve", elements: ["House"], storage: ["Battery"] },
    { name: "Solar room", kind: "headroom", elements: ["Solar"], storage: ["Battery"] },
  ]);

  it("records which reserves and headroom each node holds and counts toward", () => {
    expect(reserveTooltipLines(roles.get("Battery"))).toEqual([
      "Holds reserve: Backup, Essentials",
      "Holds headroom: Solar room",
    ]);
    expect(reserveTooltipLines(roles.get("Solar"))).toEqual([
      "Counted in reserve: Backup",
      "Counted in headroom: Solar room",
    ]);
    expect(reserveTooltipLines(roles.get("Grid"))).toEqual([]);
  });

  it("marks each kind a node holds once", () => {
    expect(reserveMarkers(roles.get("Battery"))).toBe("🛡 ⤒");
    expect(reserveMarkers(roles.get("House"))).toBe("");
    expect(reserveMarkers(undefined)).toBe("");
  });

  it("returns no roles without reserves", () => {
    expect(reserveRoles(undefined).size).toBe(0);
  });
});
