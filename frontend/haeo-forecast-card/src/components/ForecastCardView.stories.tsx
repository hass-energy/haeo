import type { Meta, StoryObj } from "@storybook/preact";

import { scenarioFixture } from "../fixtures/scenarioFixture";
import { ForecastCardStore } from "../store";
import { ResponsiveStoryFrame } from "./ResponsiveStoryFrame";

const meta: Meta = {
  title: "ForecastCard/ForecastCardView",
};

export default meta;
type Story = StoryObj;

function makeStore(): ForecastCardStore {
  const store = new ForecastCardStore();
  store.setConfig({
    type: "custom:haeo-forecast-card",
    title: "Scenario 4 forecast",
    animation_mode: "off",
  });
  store.setHass(scenarioFixture);
  return store;
}

export const Default: Story = {
  render: () => {
    const store = makeStore();
    return <ResponsiveStoryFrame store={store} />;
  },
};

export const Hovered: Story = {
  render: () => {
    const store = makeStore();
    return <ResponsiveStoryFrame store={store} initialPointer={{ x: 520, y: 120 }} />;
  },
};
