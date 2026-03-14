import type { Meta, StoryObj } from "@storybook/preact";

import { getScenarioFixture } from "../fixtures/scenarioFixtures";
import { ForecastCardStore } from "../store";
import { CARD_STYLES } from "../styles";
import { PowerStackLayer } from "./PowerStackLayer";
import type { StoryDataMode, StoryScenario } from "../fixtures/scenarioFixtures";

interface StoryArgs {
  scenario: StoryScenario;
  dataMode: StoryDataMode;
}

const meta: Meta<StoryArgs> = {
  title: "ForecastCard/PowerStackLayer",
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
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card", animation_mode: "off" });
    store.setHass(getScenarioFixture(args.scenario, args.dataMode));
    store.setSize(1000, 320);
    return (
      <div>
        <style>{CARD_STYLES}</style>
        <svg viewBox={`0 0 ${store.width} ${store.height}`} height={store.height}>
          <PowerStackLayer
            shapes={store.powerShapes}
            highlightedSeries={null}
            hoveredSeriesKeys={new Set(store.powerSeries.slice(0, 2).map((series) => series.key))}
            focusedSeriesKeys={new Set()}
          />
        </svg>
      </div>
    );
  },
};
