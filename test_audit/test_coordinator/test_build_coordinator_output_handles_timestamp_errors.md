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
  nodeid: tests/test_coordinator.py::test_build_coordinator_output_handles_timestamp_errors
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_build_coordinator_output_handles_timestamp_errors
  fixtures: []
  markers: []
notes:
  behavior: Clears forecast when timestamp conversion fails.
  redundancy: Unique error branch for forecast conversion.
  decision_rationale: Keep. Prevents bad forecast payloads.
---

# Behavior summary

When datetime conversion fails, forecast payload is suppressed.

# Redundancy / overlap

No overlap with other output behaviors.

# Decision rationale

Keep. Ensures graceful handling of bad timestamps.

# Fixtures / setup

Mocks timestamp conversion failure.

# Next actions

None.
