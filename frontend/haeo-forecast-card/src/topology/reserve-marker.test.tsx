import { render } from "preact";
import { afterEach, describe, expect, it } from "vitest";

import { NetworkTopology } from "./NetworkTopology";
import { renderTopologySvg } from "./render-svg";
import type { TopologyData } from "./types";

const topology: TopologyData = {
  nodes: [
    { name: "Battery", type: "battery", group: "Battery" },
    { name: "House", type: "load", group: "House" },
    { name: "Bus", type: "node", group: "Bus" },
  ],
  edges: [
    { name: "Battery:discharge", source: "Battery", target: "Bus", segments: [] },
    { name: "House:connection", source: "Bus", target: "House", segments: [] },
  ],
  groups: { Battery: ["Battery"], Bus: ["Bus"], House: ["House"] },
  reserves: [{ name: "Backup", elements: ["House"], storage: ["Battery"] }],
};

async function waitFor(condition: () => boolean): Promise<void> {
  for (let attempt = 0; attempt < 100 && !condition(); attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
}

describe("reserve markers", () => {
  const root = document.createElement("div");

  afterEach(() => {
    render(null, root);
  });

  it("marks only the battery holding the reserve in the exported svg", async () => {
    const svg = await renderTopologySvg(topology);

    expect(svg.match(/🛡/gu)).toHaveLength(1);
  });

  it("marks only the battery holding the reserve in the card", async () => {
    render(<NetworkTopology topology={topology} />, root);
    await waitFor(() => root.querySelector("svg") !== null);

    expect(root.textContent.match(/🛡/gu)).toHaveLength(1);
  });
});
