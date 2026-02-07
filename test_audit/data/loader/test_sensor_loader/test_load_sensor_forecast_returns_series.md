---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/data/loader/test_sensor_loader.py::test_load_sensor_forecast_returns_series
  source_file: tests/data/loader/test_sensor_loader.py
  test_class: ''
  test_function: test_load_sensor_forecast_returns_series
  fixtures: []
  markers: []
notes:
  behavior: Forecast sensors return extracted timestamp/value series.
  redundancy: Unique forecast extraction path.
  decision_rationale: Keep. Validates forecast payload handling.
---

# Behavior summary

Forecast sensors return time-series payloads from extraction.

# Redundancy / overlap

No overlap with missing/unavailable cases.

# Decision rationale

Keep. Ensures forecast handling.

# Fixtures / setup

Mocks extractor output.

# Next actions

None.
