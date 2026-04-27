import type { Meta, StoryObj } from "@storybook/preact";
import { NetworkTopology } from "./NetworkTopology";
import type { TopologyData } from "./types";

const sampleTopology: TopologyData = {
  nodes: [
    { name: "Switchboard", type: "node", group: "Switchboard" },
    { name: "Grid", type: "node", group: "Grid" },
    { name: "Battery", type: "battery", group: "Battery" },
    { name: "Solar", type: "node", group: "Solar" },
    { name: "Inverter", type: "node", group: "Inverter" },
    { name: "Load", type: "node", group: "Load" },
  ],
  edges: [
    {
      name: "Grid:import",
      source: "Grid",
      target: "Switchboard",
      segments: [
        { id: "pricing", type: "PricingSegment" },
        { id: "power_limit", type: "PowerLimitSegment" },
      ],
    },
    {
      name: "Grid:export",
      source: "Switchboard",
      target: "Grid",
      segments: [{ id: "pricing", type: "PricingSegment" }],
    },
    {
      name: "Solar:connection",
      source: "Solar",
      target: "Inverter",
      segments: [{ id: "power_limit", type: "PowerLimitSegment" }],
    },
    {
      name: "Inverter:dc_to_ac",
      source: "Inverter",
      target: "Switchboard",
      segments: [{ id: "efficiency", type: "EfficiencySegment" }],
    },
    {
      name: "Inverter:ac_to_dc",
      source: "Switchboard",
      target: "Inverter",
      segments: [{ id: "passthrough", type: "PassthroughSegment" }],
    },
    {
      name: "Battery:discharge",
      source: "Battery",
      target: "Inverter",
      segments: [{ id: "efficiency", type: "EfficiencySegment" }],
    },
    {
      name: "Battery:charge",
      source: "Inverter",
      target: "Battery",
      segments: [{ id: "passthrough", type: "PassthroughSegment" }],
    },
    {
      name: "Load:connection",
      source: "Switchboard",
      target: "Load",
      segments: [{ id: "power_limit", type: "PowerLimitSegment" }],
    },
  ],
  groups: {
    Switchboard: ["Switchboard"],
    Grid: ["Grid"],
    Battery: ["Battery"],
    Solar: ["Solar"],
    Inverter: ["Inverter"],
    Load: ["Load"],
  },
};

const meta: Meta<typeof NetworkTopology> = {
  title: "Topology/NetworkTopology",
  component: NetworkTopology,
};

export default meta;
type Story = StoryObj<typeof NetworkTopology>;

export const Default: Story = {
  args: {
    topology: sampleTopology,
  },
};

export const WithGroupedBattery: Story = {
  args: {
    topology: {
      ...sampleTopology,
      nodes: [
        ...sampleTopology.nodes.filter((n) => n.name !== "Battery"),
        { name: "BatteryCell1", type: "battery", group: "Battery" },
        { name: "BatteryCell2", type: "battery", group: "Battery" },
      ],
      edges: sampleTopology.edges.map((e) =>
        e.source === "Battery"
          ? { ...e, source: "BatteryCell1" }
          : e.target === "Battery"
            ? { ...e, target: "BatteryCell1" }
            : e
      ),
      groups: {
        ...sampleTopology.groups,
        Battery: ["BatteryCell1", "BatteryCell2"],
      },
    },
  },
};
