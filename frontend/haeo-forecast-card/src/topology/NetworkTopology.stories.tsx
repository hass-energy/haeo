import type { Meta, StoryObj } from "@storybook/preact";
import { NetworkTopology } from "./NetworkTopology";
import type { TopologyData } from "./types";
import type { HassEntityState } from "../series";

type ScenarioStates = Record<string, HassEntityState | undefined>;

const scenarioModules = import.meta.glob<ScenarioStates>("../../../../tests/scenarios/scenario*/outputs.json", {
  eager: true,
  import: "default",
});

function scenarioNameFromPath(path: string): string | null {
  const match = /\/(scenario\d+)\/outputs\.json$/.exec(path);
  return match ? (match[1] ?? null) : null;
}

function getTopologyFromScenario(scenarioName: string): TopologyData | null {
  for (const [path, states] of Object.entries(scenarioModules)) {
    if (scenarioNameFromPath(path) !== scenarioName) continue;
    // Find the optimizer status entity
    for (const [, entity] of Object.entries(states)) {
      const topo = (entity as Record<string, unknown> | undefined)?.["attributes"] as Record<string, unknown> | undefined;
      if (topo?.["topology"] != null) {
        return topo["topology"] as TopologyData;
      }
    }
  }
  return null;
}

const meta: Meta<typeof NetworkTopology> = {
  title: "Topology/NetworkTopology",
  component: NetworkTopology,
};

export default meta;
type Story = StoryObj<typeof NetworkTopology>;

export const Scenario1: Story = {
  args: {
    topology: getTopologyFromScenario("scenario1") ?? ({} as TopologyData),
  },
};

export const SimpleGrid: Story = {
  args: {
    topology: {
      nodes: [
        { name: "Switchboard", type: "node", group: "Switchboard" },
        { name: "Grid", type: "grid", group: "Grid" },
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
