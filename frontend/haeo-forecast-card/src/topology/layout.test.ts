import { describe, expect, it } from "vitest";

import { computeLayout } from "./layout";
import type { TopologyData } from "./types";

describe("computeLayout", () => {
  it("draws a connection between two nodes of one group inside that group, through its pill", async () => {
    const topology: TopologyData = {
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
          tags: [1],
        },
      ],
      groups: { Bus: ["Bus"], EV: ["EV", "EV:trip"] },
    };

    const layout = await computeLayout(topology);
    const group = layout.groups.find((item) => item.id === "group:EV");

    expect(group?.internalEdges.map((edge) => edge.name)).toEqual(
      expect.arrayContaining(["int:EV:trip_connection:a", "int:EV:trip_connection:b"])
    );
    expect(group?.children.some((child) => child.id === "pill:EV:trip_connection")).toBe(true);
  });
});
