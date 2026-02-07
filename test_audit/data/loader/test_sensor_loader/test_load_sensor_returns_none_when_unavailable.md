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
  nodeid: tests/data/loader/test_sensor_loader.py::test_load_sensor_returns_none_when_unavailable
  source_file: tests/data/loader/test_sensor_loader.py
  test_class: ''
  test_function: test_load_sensor_returns_none_when_unavailable
  fixtures: []
  markers: []
notes:
  behavior: Returns None when sensor state is unavailable.
  redundancy: Distinct from missing sensor case.
  decision_rationale: Keep. Unavailable state is a common edge case.
---

# Behavior summary

Unavailable sensor states return None.

# Redundancy / overlap

Distinct from missing sensor case.

# Decision rationale

Keep. Ensures correct handling of unavailable states.

# Fixtures / setup

Uses Home Assistant state.

# Next actions

None.
