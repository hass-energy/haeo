import type { Meta, StoryObj } from "@storybook/preact";

import { Tooltip } from "./Tooltip";

const meta: Meta<typeof Tooltip> = {
  title: "ForecastCard/Tooltip",
  component: Tooltip,
};

export default meta;
type Story = StoryObj<typeof Tooltip>;

export const Default: Story = {
  render: () => (
    <Tooltip
      locale="en"
      panelTimeMs={Date.parse("2025-10-06T10:55:00.000000+0000")}
      rows={[
        {
          key: "load-actual",
          label: "Constant load power",
          value: 2.1,
          unit: "kW",
          color: "#4f46e5",
          lane: "consumed",
        },
        {
          key: "load-forecast",
          label: "Constant load forecast",
          value: 2.8,
          unit: "kW",
          color: "#818cf8",
          lane: "possible",
        },
      ]}
      emphasizedKeys={new Set(["load-actual"])}
    />
  ),
};
