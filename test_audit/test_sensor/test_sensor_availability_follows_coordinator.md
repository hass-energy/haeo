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
  nodeid: tests/test_sensor.py::test_sensor_availability_follows_coordinator
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_sensor_availability_follows_coordinator
  fixtures: []
  markers: []
notes:
  behavior: Sensor availability mirrors coordinator last_update_success.
  redundancy: Distinct availability behavior.
  decision_rationale: Keep. Availability should reflect coordinator status.
---

# Behavior summary

Ensures sensor availability tracks coordinator update success state.

# Redundancy / overlap

No overlap with update data tests.

# Decision rationale

Keep. Availability logic is critical.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator.

# Next actions

None.
