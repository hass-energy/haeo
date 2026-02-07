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
  nodeid: tests/test_transform_sensor.py::test_main_invalid_transform
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_main_invalid_transform
  fixtures: []
  markers: []
notes:
  behavior: Returns exit code 1 when day_offset transform is missing its required parameter.
  redundancy: CLI-level counterpart to _apply_transform missing parameter test.
  decision_rationale: Keep. Validates CLI handling of missing parameters.
---

# Behavior summary

Runs `main()` with day_offset but without the required parameter and asserts exit code 1.

# Redundancy / overlap

Overlaps with unit-level missing-parameter test but at CLI boundary.

# Decision rationale

Keep. Confirms CLI error handling is consistent.

# Fixtures / setup

Uses `tmp_path` and `sample_solar_data`.

# Next actions

None.
