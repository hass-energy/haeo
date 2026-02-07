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
  nodeid: tests/data/loader/test_time_series_loader.py::test_load_boundaries_raises_when_no_data_available
  source_file: tests/data/loader/test_time_series_loader.py
  test_class: ''
  test_function: test_load_boundaries_raises_when_no_data_available
  fixtures: []
  markers: []
notes:
  behavior: Raises when boundary load has unavailable sensor data.
  redundancy: Boundary-specific unavailable state handling.
  decision_rationale: Keep. Ensures boundary path handles unavailable sensors.
---

# Behavior summary

Unavailable boundary sensor data raises a ValueError.

# Redundancy / overlap

Distinct from interval unavailable sensor test.

# Decision rationale

Keep. Ensures error handling for boundary loads.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
