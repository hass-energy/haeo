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
  nodeid: tests/test_coordinator.py::test_build_coordinator_output_sets_status_options
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_build_coordinator_output_sets_status_options
  fixtures: []
  markers: []
notes:
  behavior: Sets status sensor options and state based on output payload.
  redundancy: Unique to status output handling.
  decision_rationale: Keep. Status outputs differ from numeric sensors.
---

# Behavior summary

Status outputs include options and resolved state.

# Redundancy / overlap

No overlap with numeric output handling.

# Decision rationale

Keep. Ensures status output formatting.

# Fixtures / setup

Uses status output in output build.

# Next actions

None.
