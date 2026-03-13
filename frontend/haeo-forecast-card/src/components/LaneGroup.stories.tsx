import type { Meta, StoryObj } from "@storybook/preact";

import { scenarioFixture } from "../fixtures/scenarioFixture";
import { normalizeSeries } from "../series";
import { ForecastCardStore } from "../store";
import { CARD_STYLES } from "../styles";
import { LaneGroup } from "./LaneGroup";

const meta: Meta<typeof LaneGroup> = {
  title: "ForecastCard/LaneGroup",
  component: LaneGroup,
};

export default meta;
type Story = StoryObj<typeof LaneGroup>;

export const PowerLane: Story = {
  render: () => {
    const store = new ForecastCardStore();
    store.setConfig({ type: "custom:haeo-forecast-card" });
    store.setHass(scenarioFixture);
    store.setSize(1000, 320);
    const powerSeries = normalizeSeries(scenarioFixture, { type: "custom:haeo-forecast-card" }).filter(
      (series) => series.lane === "power"
    );
    const rect = store.laneRects.get("power") ?? { top: 20, bottom: 260 };

    return (
      <div>
        <style>{CARD_STYLES}</style>
        <svg viewBox={`0 0 ${store.width} ${store.height}`} height={store.height}>
          <LaneGroup
            lane="power"
            seriesList={powerSeries}
            yScale={(lane, value) => store.yScale(lane, value)}
            xScale={(time) => store.xScale(time)}
            width={store.width}
            margins={store.margins}
            top={rect.top}
            bottom={rect.bottom}
            highlightedSeries={null}
          />
        </svg>
      </div>
    );
  },
};
