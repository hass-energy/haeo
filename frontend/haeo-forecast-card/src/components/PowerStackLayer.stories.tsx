import type { Meta, StoryObj } from "@storybook/preact";

import { scenarioFixture } from "../fixtures/scenarioFixture";
import { ForecastCardStore } from "../store";
import { CARD_STYLES } from "../styles";
import { PowerStackLayer } from "./PowerStackLayer";

const meta: Meta<typeof PowerStackLayer> = {
  title: "ForecastCard/PowerStackLayer",
  component: PowerStackLayer,
};

export default meta;
type Story = StoryObj<typeof PowerStackLayer>;

export const Default: Story = {
  render: () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setHass(scenarioFixture);
    store.setSize(1000, 320);
    return (
      <div>
        <style>{CARD_STYLES}</style>
        <svg viewBox={`0 0 ${store.width} ${store.height}`} height={store.height}>
          <PowerStackLayer
            seriesList={store.powerSeries}
            highlightedSeries={null}
            xScale={(time) => store.xScale(time)}
            yScalePower={(value) => store.yScalePower(value)}
          />
        </svg>
      </div>
    );
  },
};
