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
  nodeid: tests/test_coordinator.py::test_build_coordinator_output_handles_empty_values
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_build_coordinator_output_handles_empty_values
  fixtures: []
  markers: []
notes:
  behavior: Uses None state and no forecast when output values are empty.
  redundancy: Related to single-value case but different branch.
  decision_rationale: Keep. Empty outputs should not produce forecast.
---

# Behavior summary

Empty output values yield a None state with no forecast.

# Redundancy / overlap

Adjacent to single-value handling but distinct branch.

# Decision rationale

Keep. Empty values are a valid scenario.

# Fixtures / setup

Uses output payload with empty values.

# Next actions

None.
