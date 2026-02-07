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
  nodeid: tests/elements/battery/test_adapter.py::test_available_with_list_entity_ids_all_exist
  source_file: tests/elements/battery/test_adapter.py
  test_class: ''
  test_function: test_available_with_list_entity_ids_all_exist
  fixtures: []
  markers: []
notes:
  behavior: List entity IDs are supported when all entities exist.
  redundancy: Distinct list-ID branch.
  decision_rationale: Keep. List entity IDs are supported.
---

# Behavior summary

Availability succeeds for list entity IDs when all exist.

# Redundancy / overlap

Pairs with list-missing test.

# Decision rationale

Keep. List entity ID handling is important.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
