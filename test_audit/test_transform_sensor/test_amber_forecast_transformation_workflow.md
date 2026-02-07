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
  nodeid: tests/test_transform_sensor.py::test_amber_forecast_transformation_workflow
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_amber_forecast_transformation_workflow
  fixtures: []
  markers: []
notes:
  behavior: End-to-end wrap_forecasts workflow preserves forecast count for Amber data.
  redundancy: Integration-level coverage; complements unit wrap_forecasts tests.
  decision_rationale: Keep. Validates end-to-end CLI behavior.
---

# Behavior summary

Runs CLI wrap_forecasts on Amber data and asserts forecast count is preserved.

# Redundancy / overlap

No overlap with unit tests; this is integration-level.

# Decision rationale

Keep. Ensures CLI integration for wrap_forecasts.

# Fixtures / setup

Uses `tmp_path`.

# Next actions

None.
