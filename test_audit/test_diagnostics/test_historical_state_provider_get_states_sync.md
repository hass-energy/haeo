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
  nodeid: tests/test_diagnostics.py::test_historical_state_provider_get_states_sync
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_historical_state_provider_get_states_sync
  fixtures: []
  markers: []
notes:
  behavior: Validates recorder get_significant_states is called with expected parameters.
  redundancy: Unique sync-path coverage.
  decision_rationale: Keep. Ensures correct recorder interaction.
---

# Behavior summary

Asserts recorder is called with expected parameters and results are passed through.

# Redundancy / overlap

No overlap with async get_states tests.

# Decision rationale

Keep. Recorder interaction is core behavior.

# Fixtures / setup

Uses recorder stubs.

# Next actions

None.
