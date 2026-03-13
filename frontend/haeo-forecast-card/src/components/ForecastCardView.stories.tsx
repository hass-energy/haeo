import type { Meta, StoryObj } from "@storybook/preact";

import { scenarioFixture } from "../fixtures/scenarioFixture";
import { ForecastCardStore } from "../store";
import { ForecastCardView } from "./ForecastCardView";

const meta: Meta<typeof ForecastCardView> = {
  title: "ForecastCard/ForecastCardView",
  component: ForecastCardView,
};

export default meta;
type Story = StoryObj<typeof ForecastCardView>;

function makeStore(): ForecastCardStore {
  const store = new ForecastCardStore();
  store.setConfig({ type: "custom:haeo-forecast-card", title: "Storybook forecast" });
  store.setHass(scenarioFixture);
  store.setSize(1100, 380);
  return store;
}

export const Default: Story = {
  render: () => {
    const store = makeStore();
    return <ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />;
  },
};

export const Hovered: Story = {
  render: () => {
    const store = makeStore();
    store.setPointer(520, 120);
    return <ForecastCardView store={store} onPointerMove={() => undefined} onPointerLeave={() => undefined} />;
  },
};
