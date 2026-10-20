import { describe, expect, it } from "vitest";

import { computeLayout } from "./layout";
import type { TopologyData } from "./types";

/** An EV whose pack connects to its trips inside the EV's group, carrying the given VLAN tags. */
function evTopology(tripTags: number[]): TopologyData {
  return {
    nodes: [
      { name: "EV", type: "ev", group: "EV" },
      { name: "EV:trip", type: "ev", group: "EV" },
      { name: "Bus", type: "node", group: "Bus" },
    ],
    edges: [
      { name: "EV:charge", source: "Bus", target: "EV", segments: [] },
      {
        name: "EV:trip_connection",
        source: "EV",
        target: "EV:trip",
        segments: [{ id: "power_limit", type: "PowerLimitSegment" }],
        tags: tripTags,
      },
    ],
    groups: { Bus: ["Bus"], EV: ["EV", "EV:trip"] },
  };
}

describe("computeLayout", () => {
  it("draws a connection between two nodes of one group inside that group, through its pill", async () => {
    const layout = await computeLayout(evTopology([1]));
    const group = layout.groups.find((item) => item.id === "group:EV");

    expect(group?.internalEdges.map((edge) => edge.name)).toEqual(
      expect.arrayContaining(["int:EV:trip_connection:a", "int:EV:trip_connection:b"])
    );
    expect(group?.children.some((child) => child.id === "pill:EV:trip_connection")).toBe(true);
  });

  it("makes room in a group for the stripes of a connection inside it", async () => {
    const nodeHeight = async (tripTags: number[]): Promise<number | undefined> => {
      const layout = await computeLayout(evTopology(tripTags));
      const group = layout.groups.find((item) => item.id === "group:EV");
      return group?.children.find((child) => child.id === "EV")?.height;
    };
    const manyTags = Array.from({ length: 20 }, (_, idx) => idx + 1);

    expect(await nodeHeight(manyTags)).toBeGreaterThan((await nodeHeight([])) ?? 0);
  });
});
