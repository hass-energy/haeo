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
  nodeid: tests/test_sensor.py::test_handle_coordinator_update_scales_percentage_outputs
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_handle_coordinator_update_scales_percentage_outputs
  fixtures: []
  markers: []
notes:
  behavior: Scales ratio outputs to percentage values, including forecast scaling.
  redundancy: Distinct scaling logic; no overlap.
  decision_rationale: Keep. Validates percent scaling behavior.
---

# Behavior summary

Verifies percentage outputs are scaled from ratio to percent for state and forecast.

# Redundancy / overlap

No overlap with other update tests.

# Decision rationale

Keep. Scaling is critical for percentage outputs.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator data.

# Next actions

None.
