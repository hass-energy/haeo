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
  nodeid: tests/test_services.py::test_save_diagnostics_service_entry_not_loaded
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_save_diagnostics_service_entry_not_loaded
  fixtures: []
  markers: []
notes:
  behavior: Raises config_entry_not_loaded for save_diagnostics when entry is not loaded.
  redundancy: Overlaps with optimize entry-not-loaded test.
  decision_rationale: Combine with optimize entry-not-loaded test via parametrization.
---

# Behavior summary

Asserts save_diagnostics raises config_entry_not_loaded for an unloaded entry.

# Redundancy / overlap

Overlaps with optimize entry-not-loaded test.

# Decision rationale

Combine. Parameterize service name and expected error.

# Fixtures / setup

Uses Home Assistant fixtures and a mock entry.

# Next actions

Consider merging with `test_optimize_service_entry_not_loaded`.
