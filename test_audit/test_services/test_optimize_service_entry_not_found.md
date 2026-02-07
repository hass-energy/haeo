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
  nodeid: tests/test_services.py::test_optimize_service_entry_not_found
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_optimize_service_entry_not_found
  fixtures: []
  markers: []
notes:
  behavior: Raises config_entry_not_found for optimize when entry ID is invalid.
  redundancy: Overlaps with diagnostics entry-not-found test.
  decision_rationale: Combine with diagnostics entry-not-found test.
---

# Behavior summary

Asserts optimize service raises config_entry_not_found for a missing config entry.

# Redundancy / overlap

Overlaps with diagnostics entry-not-found test.

# Decision rationale

Combine. Parameterize service name and expected error.

# Fixtures / setup

Uses Home Assistant fixtures.

# Next actions

Consider merging with `test_save_diagnostics_service_entry_not_found`.
