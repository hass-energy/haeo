import type { Meta, StoryObj } from "@storybook/preact";

import { scenarioFixture } from "../fixtures/scenarioFixture";
import { ForecastCardStore } from "../store";
import type { PowerDisplayMode } from "../types";
import { ResponsiveStoryFrame } from "./ResponsiveStoryFrame";

interface StoryArgs {
  powerDisplayMode: PowerDisplayMode;
}

const meta: Meta<StoryArgs> = {
  title: "ForecastCard/ForecastCardView",
  args: {
    powerDisplayMode: "opposed",
  },
  argTypes: {
    powerDisplayMode: {
      control: { type: "inline-radio" },
      options: ["opposed", "overlay"],
    },
  },
};

export default meta;
type Story = StoryObj<StoryArgs>;

function makeStore(powerDisplayMode: PowerDisplayMode): ForecastCardStore {
  const store = new ForecastCardStore();
  store.setConfig({
    type: "custom:haeo-forecast-card",
    title: "Scenario 1 forecast",
    animation_mode: "off",
    power_display_mode: powerDisplayMode,
  });
  store.setHass(scenarioFixture);
  return store;
}

export const Default: Story = {
  render: (args) => {
    const store = makeStore(args.powerDisplayMode);
    return <ResponsiveStoryFrame store={store} />;
  },
};

export const Hovered: Story = {
  render: (args) => {
    const store = makeStore(args.powerDisplayMode);
    return <ResponsiveStoryFrame store={store} initialPointer={{ x: 520, y: 120 }} />;
  },
};
