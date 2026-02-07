---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_transform_sensor.py::test_main_with_day_offset
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_main_with_day_offset
  fixtures: []
  markers: []
notes:
  behavior: Runs main with day_offset and asserts exit code 0 with printed output.
  redundancy: Overlaps with solar workflow end-to-end day_offset test.
  decision_rationale: Combine with solar workflow or keep only one end-to-end day_offset test.
---

# Behavior summary

Invokes `main()` with day_offset and asserts it completes successfully.

# Redundancy / overlap

Overlaps with `test_solar_forecast_transformation_workflow`.

# Decision rationale

Combine. Prefer one end-to-end day_offset test with stronger assertions.

# Fixtures / setup

Uses `tmp_path` and `sample_solar_data`.

# Next actions

Consider merging assertions into `test_solar_forecast_transformation_workflow`.
