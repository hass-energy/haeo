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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_time_series_loader_load_present_only
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_time_series_loader_load_present_only
  fixtures: []
  markers: []
notes:
  behavior: Broadcasts summed present values when no forecast exists.
  redundancy: Unit-level present-only path.
  decision_rationale: Keep. Ensures present-only behavior.
---

# Behavior summary

Present-only inputs are broadcast across intervals.

# Redundancy / overlap

Complementary to integration tests.

# Decision rationale

Keep. Present-only path is important.

# Fixtures / setup

Uses monkeypatched load_sensors.

# Next actions

None.
