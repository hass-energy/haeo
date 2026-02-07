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
  nodeid: tests/test_sensor.py::test_handle_coordinator_update_without_data_leaves_sensor_empty
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_handle_coordinator_update_without_data_leaves_sensor_empty
  fixtures: []
  markers: []
notes:
  behavior: Clears native value and keeps base attributes when coordinator data is empty.
  redundancy: Overlaps with missing-output test; both clear value when data is unavailable.
  decision_rationale: Combine with missing-output test into a single empty/missing data case.
---

# Behavior summary

When coordinator data is empty, sensor clears value while retaining base attributes.

# Redundancy / overlap

Overlaps with missing-output test for empty data handling.

# Decision rationale

Combine. Parametrize empty data vs missing output.

# Fixtures / setup

Uses Home Assistant fixtures and empty coordinator data.

# Next actions

Consider merging with `test_handle_coordinator_update_missing_output_clears_value`.
