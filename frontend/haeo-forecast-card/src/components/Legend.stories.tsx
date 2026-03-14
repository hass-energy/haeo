import type { Meta, StoryObj } from "@storybook/preact";

import { getScenarioFixture } from "../fixtures/scenarioFixtures";
import { normalizeSeries } from "../series";
import { CARD_STYLES } from "../styles";
import { Legend } from "./Legend";
import type { StoryDataMode, StoryScenario } from "../fixtures/scenarioFixtures";

interface StoryArgs {
  scenario: StoryScenario;
  dataMode: StoryDataMode;
}

const meta: Meta<StoryArgs> = {
  title: "ForecastCard/Legend",
  args: {
    scenario: "scenario1",
    dataMode: "mixed",
  },
  argTypes: {
    scenario: {
      control: { type: "inline-radio" },
      options: ["scenario1", "scenario2", "scenario3", "scenario4", "scenario5"],
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
          highlightedSeries={null}
          hoveredElement={null}
          hiddenSeriesKeys={new Set()}
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
