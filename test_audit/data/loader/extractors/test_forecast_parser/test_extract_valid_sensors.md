---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: amber2mqtt-Single Amber2MQTT forecast entry (consumption)
      reviewed: true
      decision: keep
      behavior: Parses Amber2MQTT consumption forecast format.
      redundancy: Covers Amber2MQTT format variant.
    - id: amber2mqtt-Multiple Amber2MQTT forecast entries
      reviewed: true
      decision: keep
      behavior: Parses multiple Amber2MQTT forecast entries.
      redundancy: Covers Amber2MQTT multi-entry variant.
    - id: amber2mqtt-Amber2MQTT feed-in sensor (advanced_price_predicted should be negated)
      reviewed: true
      decision: keep
      behavior: Parses Amber2MQTT feed-in forecast with negated prices.
      redundancy: Covers Amber2MQTT feed-in variant.
    - id: amber2mqtt-Amber2MQTT feedin sensor (alternative naming, advanced_price_predicted should be negated)
      reviewed: true
      decision: keep
      behavior: Parses Amber2MQTT feed-in forecast with alternate naming.
      redundancy: Covers Amber2MQTT naming variant.
    - id: amber2mqtt-Amber2MQTT forecast with datetime objects instead of strings
      reviewed: true
      decision: keep
      behavior: Parses Amber2MQTT forecasts with datetime objects.
      redundancy: Covers datetime vs string timestamp variant.
    - id: amberelectric-Single Amber forecast entry
      reviewed: true
      decision: keep
      behavior: Parses single Amber Electric forecast entry.
      redundancy: Covers Amber Electric single-entry variant.
    - id: amberelectric-Multiple Amber forecast entries
      reviewed: true
      decision: keep
      behavior: Parses multiple Amber Electric forecast entries.
      redundancy: Covers Amber Electric multi-entry variant.
    - id: amberelectric-Amber forecast with timezone conversion
      reviewed: true
      decision: keep
      behavior: Parses Amber Electric forecast with timezone conversion.
      redundancy: Covers timezone conversion variant.
    - id: amberelectric-Amber forecast with datetime objects instead of strings
      reviewed: true
      decision: keep
      behavior: Parses Amber Electric forecasts with datetime objects.
      redundancy: Covers datetime vs string timestamp variant.
    - id: aemo_nem-Single AEMO forecast entry
      reviewed: true
      decision: keep
      behavior: Parses single AEMO NEM forecast entry.
      redundancy: Covers AEMO single-entry variant.
    - id: aemo_nem-Multiple AEMO forecast entries
      reviewed: true
      decision: keep
      behavior: Parses multiple AEMO NEM forecast entries.
      redundancy: Covers AEMO multi-entry variant.
    - id: emhass-EMHASS load forecast with forecasts attribute
      reviewed: true
      decision: keep
      behavior: Parses EMHASS load forecast from forecasts attribute.
      redundancy: Covers EMHASS forecasts attribute variant.
    - id: emhass-EMHASS deferrable load with deferrables_schedule attribute
      reviewed: true
      decision: keep
      behavior: Parses EMHASS deferrable load schedule.
      redundancy: Covers EMHASS deferrables_schedule variant.
    - id: emhass-EMHASS forecast with numeric values (not strings)
      reviewed: true
      decision: keep
      behavior: Parses EMHASS numeric forecast values.
      redundancy: Covers numeric value variant.
    - id: emhass-EMHASS battery power with battery_scheduled_power attribute
      reviewed: true
      decision: keep
      behavior: Parses EMHASS battery scheduled power.
      redundancy: Covers battery_scheduled_power variant.
    - id: emhass-EMHASS battery SOC with battery_scheduled_soc attribute
      reviewed: true
      decision: keep
      behavior: Parses EMHASS battery scheduled SOC.
      redundancy: Covers battery_scheduled_soc variant.
    - id: emhass-EMHASS unit cost forecast with unit_load_cost_forecasts attribute
      reviewed: true
      decision: keep
      behavior: Parses EMHASS unit load cost forecasts.
      redundancy: Covers unit_load_cost_forecasts variant.
    - id: emhass-EMHASS ML forecaster with scheduled_forecast attribute
      reviewed: true
      decision: keep
      behavior: Parses EMHASS scheduled_forecast output.
      redundancy: Covers scheduled_forecast variant.
    - id: emhass-EMHASS temperature forecast with predicted_temperatures attribute
      reviewed: true
      decision: keep
      behavior: Parses EMHASS predicted temperature forecast.
      redundancy: Covers predicted_temperatures variant.
    - id: flow_power-Flow Power export price with two periods
      reviewed: true
      decision: keep
      behavior: Parses Flow Power export price forecast.
      redundancy: Covers Flow Power format variant.
    - id: haeo-Single HAEO forecast entry with power
      reviewed: true
      decision: keep
      behavior: Parses single HAEO forecast entry with power.
      redundancy: Covers HAEO single-entry variant.
    - id: haeo-Multiple HAEO forecast entries
      reviewed: true
      decision: keep
      behavior: Parses multiple HAEO forecast entries.
      redundancy: Covers HAEO multi-entry variant.
    - id: haeo-HAEO forecast with datetime objects
      reviewed: true
      decision: keep
      behavior: Parses HAEO forecasts with datetime objects.
      redundancy: Covers datetime vs string timestamp variant.
    - id: haeo-HAEO forecast with energy device class
      reviewed: true
      decision: keep
      behavior: Parses HAEO forecast with energy device class.
      redundancy: Covers device class mapping variant.
    - id: haeo-HAEO forecast without device_class attribute
      reviewed: true
      decision: keep
      behavior: Parses HAEO forecast without device_class.
      redundancy: Covers missing device_class variant.
    - id: haeo-HAEO forecast with integer values (should be converted to float)
      reviewed: true
      decision: keep
      behavior: Parses HAEO forecast with integer values as floats.
      redundancy: Covers numeric conversion variant.
    - id: haeo-HAEO forecast with invalid device_class (should be ignored)
      reviewed: true
      decision: keep
      behavior: Parses HAEO forecast and ignores invalid device_class.
      redundancy: Covers invalid device_class variant.
    - id: solcast_solar-Single Solcast forecast entry
      reviewed: true
      decision: keep
      behavior: Parses single Solcast forecast entry.
      redundancy: Covers Solcast single-entry variant.
    - id: solcast_solar-Multiple Solcast forecast entries
      reviewed: true
      decision: keep
      behavior: Parses multiple Solcast forecast entries.
      redundancy: Covers Solcast multi-entry variant.
    - id: solcast_solar-Solcast forecast with datetime objects instead of strings
      reviewed: true
      decision: keep
      behavior: Parses Solcast forecast with datetime objects.
      redundancy: Covers datetime vs string timestamp variant.
    - id: solcast_solar-Solcast forecast with mixed string and datetime object timestamps
      reviewed: true
      decision: keep
      behavior: Parses Solcast forecast with mixed timestamp types.
      redundancy: Covers mixed timestamp variant.
    - id: open_meteo_solar_forecast-Open-Meteo forecast with watts dict
      reviewed: true
      decision: keep
      behavior: Parses Open-Meteo forecast using watts dict format.
      redundancy: Covers Open-Meteo watts dict variant.
    - id: open_meteo_solar_forecast-Multiple Open-Meteo forecast entries
      reviewed: true
      decision: keep
      behavior: Parses multiple Open-Meteo forecast entries.
      redundancy: Covers Open-Meteo multi-entry variant.
meta:
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::test_extract_valid_sensors
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: ''
  test_function: test_extract_valid_sensors
  fixtures: []
  markers: []
notes:
  behavior: Parses all valid forecast sensor formats into expected series and units.
  redundancy: Unique broad parser coverage.
  decision_rationale: Keep. Ensures supported formats work.
---

# Behavior summary

Valid forecast sensor payloads are parsed into correct series and units.

# Redundancy / overlap

No overlap; this is the primary valid-format coverage.

# Decision rationale

Keep. Broad format coverage is essential.

# Fixtures / setup

Uses ALL_VALID_SENSORS fixtures.

# Next actions

None.
