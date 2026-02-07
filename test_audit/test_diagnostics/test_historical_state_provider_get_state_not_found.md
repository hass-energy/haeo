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
  nodeid: tests/test_diagnostics.py::test_historical_state_provider_get_state_not_found
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_historical_state_provider_get_state_not_found
  fixtures: []
  markers: []
notes:
  behavior: Returns None when recorder has no historical state for an entity.
  redundancy: Complementary to historical get_state success case.
  decision_rationale: Keep. Validates missing historical state handling.
---

# Behavior summary

Ensures the historical provider returns None when no state is found.

# Redundancy / overlap

No overlap with success case.

# Decision rationale

Keep. Missing data handling is required.

# Fixtures / setup

Uses Home Assistant fixtures and recorder stubs.

# Next actions

None.
