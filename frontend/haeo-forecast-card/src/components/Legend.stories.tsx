import type { Meta, StoryObj } from "@storybook/preact";

import { STORY_SCENARIOS, getScenarioFixture } from "../fixtures/scenarioFixtures";
import { normalizeSeries } from "../series";
import { CARD_STYLES } from "../styles";
import { Legend } from "./Legend";
import type { StoryDataMode, StoryScenario } from "../fixtures/scenarioFixtures";

interface StoryArgs {
  scenario: StoryScenario;
  dataMode: StoryDataMode;
}

const defaultScenario = STORY_SCENARIOS[0] ?? "scenario1";

const meta: Meta<StoryArgs> = {
  title: "ForecastCard/Legend",
  args: {
    scenario: defaultScenario,
    dataMode: "mixed",
  },
  argTypes: {
    scenario: {
      control: { type: "inline-radio" },
      options: STORY_SCENARIOS,
    },
    dataMode: {
      control: { type: "inline-radio" },
      options: ["mixed", "inputs", "outputs"],
    },
  },
};

export default meta;
type Story = StoryObj<StoryArgs>;

export const Default: Story = {
  render: (args) => {
    const series = normalizeSeries(getScenarioFixture(args.scenario, args.dataMode), {
      type: "custom:haeo-forecast-card",
    });
    return (
      <div>
        <style>{CARD_STYLES}</style>
        <Legend
          series={series}
          locale="en"
          highlightedSeries={null}
          hoveredElement={null}
          hiddenSeriesKeys={new Set()}
          visibilityRevision={0}
          powerDisplayMode="opposed"
          onHighlight={() => undefined}
          onElementHover={() => undefined}
          onToggleSeries={() => undefined}
          onToggleElement={() => undefined}
          onTogglePowerDisplayMode={() => undefined}
        />
      </div>
    );
  },
};
