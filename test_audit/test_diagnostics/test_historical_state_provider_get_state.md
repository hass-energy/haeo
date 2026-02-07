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
  nodeid: tests/test_diagnostics.py::test_historical_state_provider_get_state
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_historical_state_provider_get_state
  fixtures: []
  markers: []
notes:
  behavior: Returns historical state for an entity from the recorder.
  redundancy: Complements not-found case.
  decision_rationale: Keep. Validates historical lookup.
---

# Behavior summary

Ensures the historical provider returns recorded state for a given entity.

# Redundancy / overlap

No overlap with current provider tests.

# Decision rationale

Keep. Core historical provider behavior.

# Fixtures / setup

Uses Home Assistant fixtures and recorder stubs.

# Next actions

None.
