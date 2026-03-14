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
      hoverTimeMs={Date.parse("2025-10-06T10:55:00.000000+0000")}
      rows={[
        { key: "grid-power", label: "Grid import power", value: 2.1, unit: "kW", color: "#4f46e5" },
        { key: "battery-soc", label: "Battery SOC", value: 64.2, unit: "%", color: "#16a34a" },
      ]}
      totals={[
        { lane: "power", value: 2.1, unit: "kW" },
        { lane: "soc", value: 64.2, unit: "%" },
      ]}
      emphasizedKeys={new Set(["grid-power"])}
    />
  ),
};
