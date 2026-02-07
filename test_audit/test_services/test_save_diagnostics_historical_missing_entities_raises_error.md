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
  nodeid: tests/test_services.py::test_save_diagnostics_historical_missing_entities_raises_error
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_save_diagnostics_historical_missing_entities_raises_error
  fixtures: []
  markers: []
notes:
  behavior: Raises no_history_at_time error when historical diagnostics has missing entities.
  redundancy: Unique error path for historical diagnostics.
  decision_rationale: Keep. Validates missing-entity reporting.
---

# Behavior summary

Asserts historical diagnostics raises ServiceValidationError with the expected translation key and placeholders.

# Redundancy / overlap

No overlap with other diagnostics errors.

# Decision rationale

Keep. Error reporting for historical diagnostics is important.

# Fixtures / setup

Uses Home Assistant fixtures and temp directory.

# Next actions

None.
