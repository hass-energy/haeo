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
  nodeid: tests/entities/test_haeo_number.py::test_driven_mode_with_single_entity
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_driven_mode_with_single_entity
  fixtures: []
  markers: []
notes:
  behavior: Driven mode tracks single source entity and sets attributes.
  redundancy: Pairs with multiple-entity test.
  decision_rationale: Keep. Validates single-source behavior.
---

# Behavior summary

Driven entity sets source entity IDs and attributes.

# Redundancy / overlap

Complementary to multiple-entity test.

# Decision rationale

Keep. Ensures single source path.

# Fixtures / setup

Uses subentry with one entity ID.

# Next actions

None.
