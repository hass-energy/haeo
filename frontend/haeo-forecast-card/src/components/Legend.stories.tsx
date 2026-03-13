import type { Meta, StoryObj } from "@storybook/preact";

import { scenarioFixture } from "../fixtures/scenarioFixture";
import { normalizeSeries } from "../series";
import { CARD_STYLES } from "../styles";
import { Legend } from "./Legend";

const meta: Meta<typeof Legend> = {
  title: "ForecastCard/Legend",
  component: Legend,
};

export default meta;
type Story = StoryObj<typeof Legend>;

const series = normalizeSeries(scenarioFixture, { type: "custom:haeo-forecast-card" });

export const Default: Story = {
  render: () => (
    <div>
      <style>{CARD_STYLES}</style>
      <Legend series={series} highlightedSeries={null} onHighlight={() => undefined} />
    </div>
  ),
};
