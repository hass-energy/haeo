import { describe, expect, it } from "vitest";

import { bufferMarkers, bufferRoles, bufferTooltipLines } from "./shared";

describe("bufferRoles", () => {
  const roles = bufferRoles([
    { name: "Backup", kind: "reserve", elements: ["House", "Solar"], storage: ["Battery"] },
    { name: "Essentials", kind: "reserve", elements: ["House"], storage: ["Battery"] },
    { name: "Solar room", kind: "headroom", elements: ["Solar"], storage: ["Battery"] },
  ]);

  it("records which buffers each node holds and counts toward", () => {
    expect(bufferTooltipLines(roles.get("Battery"))).toEqual([
      "Holds buffer Backup (reserve)",
      "Holds buffer Essentials (reserve)",
      "Holds buffer Solar room (headroom)",
    ]);
    expect(bufferTooltipLines(roles.get("Solar"))).toEqual([
      "Counted in buffer Backup (reserve)",
      "Counted in buffer Solar room (headroom)",
    ]);
    expect(bufferTooltipLines(roles.get("Grid"))).toEqual([]);
  });

  it("marks each kind a node holds once", () => {
    expect(bufferMarkers(roles.get("Battery"))).toBe("🛡 ⤒");
    expect(bufferMarkers(roles.get("House"))).toBe("");
    expect(bufferMarkers(undefined)).toBe("");
  });

  it("returns no roles without buffers", () => {
    expect(bufferRoles(undefined).size).toBe(0);
  });
});
