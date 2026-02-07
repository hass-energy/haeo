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
  nodeid: tests/test_diagnostics.py::test_collect_diagnostics_returns_missing_entity_ids
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_collect_diagnostics_returns_missing_entity_ids
  fixtures: []
  markers: []
notes:
  behavior: Reports missing entity IDs and includes only found input states.
  redundancy: Complementary to all-found case; can be parameterized.
  decision_rationale: Combine with all-found case.
---

# Behavior summary

Ensures missing entity IDs are reported and inputs include only found states.

# Redundancy / overlap

Overlaps with all-found case structure.

# Decision rationale

Combine. Parameterize missing vs all-found behavior.

# Fixtures / setup

Uses Home Assistant fixtures and mock entities.

# Next actions

Consider merging with `test_collect_diagnostics_returns_empty_missing_when_all_found`.
