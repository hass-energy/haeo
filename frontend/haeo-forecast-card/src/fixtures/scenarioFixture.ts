import type { HassLike } from "../series";

export const scenarioFixture: HassLike = {
  states: {
    "sensor.grid_import_power": {
      entity_id: "sensor.grid_import_power",
      attributes: {
        element_name: "Grid",
        output_name: "import_power",
        output_type: "power",
        unit_of_measurement: "kW",
        forecast: [
          { time: "2025-10-06T10:50:00.000000+0000", value: 2.1 },
          { time: "2025-10-06T10:55:00.000000+0000", value: 1.8 },
          { time: "2025-10-06T11:00:00.000000+0000", value: 2.3 },
          { time: "2025-10-06T11:05:00.000000+0000", value: 1.2 },
        ],
      },
    },
    "sensor.grid_import_price": {
      entity_id: "sensor.grid_import_price",
      attributes: {
        element_name: "Grid",
        output_name: "import_price",
        output_type: "price",
        unit_of_measurement: "$/kWh",
        forecast: [
          { time: "2025-10-06T10:50:00.000000+0000", value: 0.21 },
          { time: "2025-10-06T10:55:00.000000+0000", value: 0.22 },
          { time: "2025-10-06T11:00:00.000000+0000", value: 0.24 },
          { time: "2025-10-06T11:05:00.000000+0000", value: 0.2 },
        ],
      },
    },
    "sensor.battery_soc": {
      entity_id: "sensor.battery_soc",
      attributes: {
        element_name: "Battery",
        output_name: "state_of_charge",
        output_type: "state_of_charge",
        unit_of_measurement: "%",
        forecast: [
          { time: "2025-10-06T10:50:00.000000+0000", value: 62.1 },
          { time: "2025-10-06T10:55:00.000000+0000", value: 63.8 },
          { time: "2025-10-06T11:00:00.000000+0000", value: 64.3 },
          { time: "2025-10-06T11:05:00.000000+0000", value: 63.9 },
        ],
      },
    },
  },
};
