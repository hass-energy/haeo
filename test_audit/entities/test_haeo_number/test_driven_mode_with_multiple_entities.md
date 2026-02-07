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
  nodeid: tests/entities/test_haeo_number.py::test_driven_mode_with_multiple_entities
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_driven_mode_with_multiple_entities
  fixtures: []
  markers: []
notes:
  behavior: Driven mode accepts multiple source entity IDs.
  redundancy: Pairs with single-entity test.
  decision_rationale: Keep. Validates multi-source handling.
---

# Behavior summary

Driven entity stores multiple source IDs.

# Redundancy / overlap

Complementary to single-source test.

# Decision rationale

Keep. Ensures multi-source path.

# Fixtures / setup

Uses subentry with two entity IDs.

# Next actions

None.
