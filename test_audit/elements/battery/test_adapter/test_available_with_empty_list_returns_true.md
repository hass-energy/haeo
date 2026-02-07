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
  nodeid: tests/elements/battery/test_adapter.py::test_available_with_empty_list_returns_true
  source_file: tests/elements/battery/test_adapter.py
  test_class: ''
  test_function: test_available_with_empty_list_returns_true
  fixtures: []
  markers: []
notes:
  behavior: Empty entity ID lists are treated as available.
  redundancy: Distinct empty-list branch.
  decision_rationale: Keep. Empty list handling should be explicit.
---

# Behavior summary

Empty lists do not block availability.

# Redundancy / overlap

Distinct from list-all-exist test.

# Decision rationale

Keep. Empty list is a supported case.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
