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
  nodeid: tests/test_services.py::test_optimize_service_wrong_domain
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_optimize_service_wrong_domain
  fixtures: []
  markers: []
notes:
  behavior: Raises config_entry_wrong_domain for optimize when entry is not HAEO.
  redundancy: Overlaps with diagnostics wrong-domain test.
  decision_rationale: Combine with diagnostics wrong-domain test.
---

# Behavior summary

Asserts optimize service raises config_entry_wrong_domain for a non-HAEO entry.

# Redundancy / overlap

Overlaps with diagnostics wrong-domain test.

# Decision rationale

Combine. Parameterize service name and expected error.

# Fixtures / setup

Uses Home Assistant fixtures and a non-HAEO entry.

# Next actions

Consider merging with `test_save_diagnostics_service_wrong_domain`.
