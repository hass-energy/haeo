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
  nodeid: tests/test_sensor_utils.py::test_get_output_sensors_handles_non_numeric_states
  source_file: tests/test_sensor_utils.py
  test_class: ''
  test_function: test_get_output_sensors_handles_non_numeric_states
  fixtures: []
  markers: []
notes:
  behavior: Preserves non-numeric state strings without error.
  redundancy: Distinct from zero-value numeric formatting.
  decision_rationale: Keep. Non-numeric state handling is separate.
---

# Behavior summary

Ensures non-numeric states are preserved when formatting output sensors.

# Redundancy / overlap

No overlap with numeric zero formatting test.

# Decision rationale

Keep. Distinct state handling.

# Fixtures / setup

Uses Home Assistant fixtures and entity states.

# Next actions

None.
