import type { Meta, StoryObj } from "@storybook/preact";

import { STORY_SCENARIOS, getScenarioFixture } from "../fixtures/scenarioFixtures";
import { ForecastCardStore } from "../store";
import type { PowerDisplayMode } from "../types";
import { ResponsiveStoryFrame } from "./ResponsiveStoryFrame";
import type { StoryDataMode, StoryScenario } from "../fixtures/scenarioFixtures";

interface StoryArgs {
  powerDisplayMode: PowerDisplayMode;
  scenario: StoryScenario;
  dataMode: StoryDataMode;
}

const defaultScenario = STORY_SCENARIOS[0] ?? "scenario1";

const meta: Meta<StoryArgs> = {
  title: "ForecastCard/ForecastCardView",
  args: {
    powerDisplayMode: "opposed",
    scenario: defaultScenario,
    dataMode: "mixed",
  },
  argTypes: {
    powerDisplayMode: {
      control: { type: "inline-radio" },
      options: ["opposed", "overlay"],
    },
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

function makeStore(
  powerDisplayMode: PowerDisplayMode,
  scenario: StoryScenario,
  dataMode: StoryDataMode
): ForecastCardStore {
  const store = new ForecastCardStore();
  store.setConfig({
    type: "custom:haeo-forecast-card",
    title: `${scenario} forecast (${dataMode})`,
    animation_mode: "off",
    power_display_mode: powerDisplayMode,
  });
  store.setHass(getScenarioFixture(scenario, dataMode));
  return store;
}

export const Default: Story = {
  render: (args) => {
    const store = makeStore(args.powerDisplayMode, args.scenario, args.dataMode);
    return <ResponsiveStoryFrame store={store} />;
  },
};

export const Hovered: Story = {
  render: (args) => {
    const store = makeStore(args.powerDisplayMode, args.scenario, args.dataMode);
    return <ResponsiveStoryFrame store={store} initialPointer={{ x: 520, y: 120 }} />;
  },
};
