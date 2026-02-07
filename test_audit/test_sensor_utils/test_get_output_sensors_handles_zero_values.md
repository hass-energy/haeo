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
  nodeid: tests/test_sensor_utils.py::test_get_output_sensors_handles_zero_values
  source_file: tests/test_sensor_utils.py
  test_class: ''
  test_function: test_get_output_sensors_handles_zero_values
  fixtures: []
  markers: []
notes:
  behavior: Formats numeric zero states correctly.
  redundancy: Distinct numeric formatting behavior.
  decision_rationale: Keep. Ensures zero values are handled consistently.
---

# Behavior summary

Checks that numeric zero values are formatted and preserved in output sensors.

# Redundancy / overlap

No overlap with non-numeric state handling.

# Decision rationale

Keep. Numeric formatting should handle zero.

# Fixtures / setup

Uses Home Assistant fixtures and entity states.

# Next actions

None.
