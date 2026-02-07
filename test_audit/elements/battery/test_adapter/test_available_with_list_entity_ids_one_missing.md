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
  nodeid: tests/elements/battery/test_adapter.py::test_available_with_list_entity_ids_one_missing
  source_file: tests/elements/battery/test_adapter.py
  test_class: ''
  test_function: test_available_with_list_entity_ids_one_missing
  fixtures: []
  markers: []
notes:
  behavior: Availability fails when one entity in list is missing.
  redundancy: Pairs with list-all-exist test.
  decision_rationale: Keep. List entity IDs must all exist.
---

# Behavior summary

Missing any entity in list makes availability false.

# Redundancy / overlap

Pairs with list-all-exist test.

# Decision rationale

Keep. List entity ID handling is important.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
