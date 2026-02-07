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
  nodeid: tests/entities/test_haeo_horizon.py::test_horizon_manager_current_start_time_none_when_no_timestamps
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_horizon_manager_current_start_time_none_when_no_timestamps
  fixtures: []
  markers: []
notes:
  behavior: current_start_time returns None when timestamps are empty.
  redundancy: Companion to current_start_time present test.
  decision_rationale: Keep. Ensures safe None handling.
---

# Behavior summary

Returns None without forecast timestamps.

# Redundancy / overlap

Complementary to start_time present test.

# Decision rationale

Keep. Validates None handling.

# Fixtures / setup

Clears forecast timestamps.

# Next actions

None.
