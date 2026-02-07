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
  nodeid: tests/test_transform_sensor.py::test_apply_wrap_forecasts_transform
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_apply_wrap_forecasts_transform
  fixtures: []
  markers: []
notes:
  behavior: Dispatches to wrap_forecasts transform and returns wrapped data.
  redundancy: Core dispatch path for wrap_forecasts.
  decision_rationale: Keep. Validates transform dispatch.
---

# Behavior summary

Calls `_apply_transform` with `wrap_forecasts` and asserts wrapped forecasts exist.

# Redundancy / overlap

No overlap with day_offset or passthrough dispatch cases.

# Decision rationale

Keep. Ensures wrap_forecasts dispatch works.

# Fixtures / setup

Uses `sample_amber_forecast_data`.

# Next actions

None.
