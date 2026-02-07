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
  nodeid: tests/test_sensor.py::test_async_setup_entry_creates_horizon_when_no_outputs
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_async_setup_entry_creates_horizon_when_no_outputs
  fixtures: []
  markers: []
notes:
  behavior: Creates the horizon entity even when coordinator output data is empty.
  redundancy: Overlaps with metadata setup test but covers empty-output edge case.
  decision_rationale: Keep. Validates horizon creation in empty-output scenarios.
---

# Behavior summary

Ensures horizon entity is created even when no output data is available.

# Redundancy / overlap

Some overlap with full setup test; adds empty-output coverage.

# Decision rationale

Keep. Empty-output behavior is distinct.

# Fixtures / setup

Uses Home Assistant fixtures and empty coordinator data.

# Next actions

None.
