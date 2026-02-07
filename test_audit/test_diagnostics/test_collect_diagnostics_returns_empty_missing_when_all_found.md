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
  nodeid: tests/test_diagnostics.py::test_collect_diagnostics_returns_empty_missing_when_all_found
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_collect_diagnostics_returns_empty_missing_when_all_found
  fixtures: []
  markers: []
notes:
  behavior: Reports no missing entity IDs when all states are found.
  redundancy: Complementary to missing-IDs case; can be parameterized.
  decision_rationale: Combine with missing-IDs case.
---

# Behavior summary

Ensures missing_entity_ids is empty when all entities are found.

# Redundancy / overlap

Overlaps with missing-IDs case structure.

# Decision rationale

Combine. Parameterize missing vs all-found behavior.

# Fixtures / setup

Uses Home Assistant fixtures and mock entities.

# Next actions

Consider merging with `test_collect_diagnostics_returns_missing_entity_ids`.
