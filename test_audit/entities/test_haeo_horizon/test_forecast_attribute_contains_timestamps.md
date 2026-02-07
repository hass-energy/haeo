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
  nodeid: tests/entities/test_haeo_horizon.py::test_forecast_attribute_contains_timestamps
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_forecast_attribute_contains_timestamps
  fixtures: []
  markers: []
notes:
  behavior: Forecast attribute is list of time/value entries with None values.
  redundancy: Specific to forecast attribute shape.
  decision_rationale: Keep. Ensures forecast format.
---

# Behavior summary

Forecast attribute contains timestamp entries with None values.

# Redundancy / overlap

Complementary to timestamp alignment test.

# Decision rationale

Keep. Protects forecast shape.

# Fixtures / setup

Uses horizon manager and entity.

# Next actions

None.
