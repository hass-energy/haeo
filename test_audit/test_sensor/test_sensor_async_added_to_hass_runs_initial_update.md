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
  nodeid: tests/test_sensor.py::test_sensor_async_added_to_hass_runs_initial_update
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_sensor_async_added_to_hass_runs_initial_update
  fixtures: []
  markers: []
notes:
  behavior: Calls coordinator update when sensor is added to hass.
  redundancy: Distinct lifecycle hook coverage.
  decision_rationale: Keep. Ensures initial update behavior.
---

# Behavior summary

Asserts `async_added_to_hass` triggers an update when data exists.

# Redundancy / overlap

No overlap with update handler tests.

# Decision rationale

Keep. Lifecycle behavior matters.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator.

# Next actions

None.
