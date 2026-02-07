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
  nodeid: tests/test_coordinator.py::test_async_update_data_returns_outputs
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_update_data_returns_outputs
  fixtures: []
  markers: []
notes:
  behavior: Runs optimization, merges adapter outputs and forecasts, and clears any failure issue.
  redundancy: Broad happy-path integration coverage; not duplicated elsewhere.
  decision_rationale: Keep. Core coordinator behavior.
---

# Behavior summary

Ensures coordinator update returns merged outputs and forecast data on the happy path.

# Redundancy / overlap

No overlap; this is the primary happy-path test.

# Decision rationale

Keep. Validates end-to-end update flow.

# Fixtures / setup

Uses mocked optimizer and adapter outputs.

# Next actions

None.
