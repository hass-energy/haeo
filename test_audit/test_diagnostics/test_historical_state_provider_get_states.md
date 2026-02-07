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
  nodeid: tests/test_diagnostics.py::test_historical_state_provider_get_states
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_historical_state_provider_get_states
  fixtures: []
  markers: []
notes:
  behavior: Returns historical states for multiple entity IDs.
  redundancy: Complementary to empty input case.
  decision_rationale: Keep. Validates batch historical lookup.
---

# Behavior summary

Ensures multiple entity states are returned from recorder for requested IDs.

# Redundancy / overlap

No overlap with empty input case.

# Decision rationale

Keep. Batch lookup is important.

# Fixtures / setup

Uses Home Assistant fixtures and recorder stubs.

# Next actions

None.
