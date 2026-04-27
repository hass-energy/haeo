import type { Meta, StoryObj } from "@storybook/preact";
import { NetworkTopology } from "./NetworkTopology";
import type { TopologyData } from "./types";
import scenario1 from "./fixtures/scenario1.json";

const meta: Meta<typeof NetworkTopology> = {
  title: "Topology/NetworkTopology",
  component: NetworkTopology,
};

export default meta;
type Story = StoryObj<typeof NetworkTopology>;

export const Scenario1: Story = {
  args: {
    topology: scenario1 as TopologyData,
  },
};

export const SimpleGrid: Story = {
  args: {
    topology: {
      nodes: [
        { name: "Switchboard", type: "node", group: "Switchboard" },
        { name: "Grid", type: "node", group: "Grid" },
      ],
      edges: [
        {
          name: "Grid:import",
          source: "Grid",
          target: "Switchboard",
          segments: [
            { id: "pricing", type: "PricingSegment" },
            { id: "power_limit", type: "PowerLimitSegment" },
          ],
        },
        {
          name: "Grid:export",
          source: "Switchboard",
          target: "Grid",
          segments: [{ id: "pricing", type: "PricingSegment" }],
        },
      ],
      groups: {
        Switchboard: ["Switchboard"],
        Grid: ["Grid"],
      },
    },
  },
};
