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
  nodeid: tests/data/loader/test_time_series_loader.py::test_load_boundaries_raises_when_sensors_missing
  source_file: tests/data/loader/test_time_series_loader.py
  test_class: ''
  test_function: test_load_boundaries_raises_when_sensors_missing
  fixtures: []
  markers: []
notes:
  behavior: Raises when any boundary sensor is unavailable.
  redundancy: Boundary-specific missing sensor handling.
  decision_rationale: Keep. Ensures missing sensors fail boundary load.
---

# Behavior summary

Missing boundary sensors cause load_boundaries to raise.

# Redundancy / overlap

Distinct from interval missing-sensor test.

# Decision rationale

Keep. Boundary path should fail fast.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
