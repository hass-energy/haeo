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

const SCENARIO_TOPOLOGIES: Record<string, TopologyData> = {};
for (const [path, states] of Object.entries(scenarioModules)) {
  const name = scenarioNameFromPath(path);
  if (name === null) continue;
  for (const entity of Object.values(states)) {
    const attrs = (entity as Record<string, unknown> | undefined)?.["attributes"] as
      | Record<string, unknown>
      | undefined;
    if (attrs?.["topology"] != null) {
      SCENARIO_TOPOLOGIES[name] = attrs["topology"] as TopologyData;
      break;
    }
  }
}

const SCENARIOS = Object.keys(SCENARIO_TOPOLOGIES).sort(
  (a, b) => Number(a.replace("scenario", "")) - Number(b.replace("scenario", ""))
);

const defaultScenario = SCENARIOS[0] ?? "scenario1";

interface StoryArgs {
  scenario: string;
}

const meta: Meta<StoryArgs> = {
  title: "Topology/NetworkTopology",
  args: {
    scenario: defaultScenario,
  },
  argTypes: {
    scenario: {
      control: { type: "inline-radio" },
      options: SCENARIOS,
    },
  },
};

export default meta;
type Story = StoryObj<StoryArgs>;

export const Default: Story = {
  render: (args) => {
    const topology = SCENARIO_TOPOLOGIES[args.scenario];
    if (topology == null) {
      return <div>No topology for {args.scenario}</div>;
    }
    return <NetworkTopology topology={topology} />;
  },
};
