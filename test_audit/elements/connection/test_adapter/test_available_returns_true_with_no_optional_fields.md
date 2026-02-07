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
  nodeid: tests/elements/connection/test_adapter.py::test_available_returns_true_with_no_optional_fields
  source_file: tests/elements/connection/test_adapter.py
  test_class: ''
  test_function: test_available_returns_true_with_no_optional_fields
  fixtures: []
  markers: []
notes:
  behavior: Availability succeeds when only required fields are configured.
  redundancy: Base availability success case.
  decision_rationale: Keep. Confirms required-only configuration is valid.
---

# Behavior summary

Connection availability succeeds with required fields only.

# Redundancy / overlap

No overlap with optional-field cases.

# Decision rationale

Keep. Required-only behavior should be valid.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
