---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_services.py::test_save_diagnostics_service_entry_not_found
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_save_diagnostics_service_entry_not_found
  fixtures: []
  markers: []
notes:
  behavior: Raises config_entry_not_found for save_diagnostics when entry ID is invalid.
  redundancy: Overlaps with optimize service entry-not-found test.
  decision_rationale: Combine with optimize entry-not-found test via parametrization.
---

# Behavior summary

Asserts save_diagnostics raises config_entry_not_found for a missing config entry.

# Redundancy / overlap

Overlaps with optimize entry-not-found test.

# Decision rationale

Combine. Parametrize service name and expected error.

# Fixtures / setup

Uses Home Assistant fixtures.

# Next actions

Consider merging with `test_optimize_service_entry_not_found`.
