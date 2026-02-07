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
  nodeid: tests/test_sensor.py::test_handle_coordinator_update_sets_direction
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_handle_coordinator_update_sets_direction
  fixtures: []
  markers: []
notes:
  behavior: Applies `direction` attribute from output data to extra state attributes.
  redundancy: Distinct attribute mapping behavior.
  decision_rationale: Keep. Validates direction metadata handling.
---

# Behavior summary

Ensures direction from output data appears in sensor extra attributes.

# Redundancy / overlap

No overlap with other attribute handling tests.

# Decision rationale

Keep. Direction metadata is important.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator data.

# Next actions

None.
