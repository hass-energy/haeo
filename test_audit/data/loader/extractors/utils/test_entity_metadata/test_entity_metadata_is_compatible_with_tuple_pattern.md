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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_entity_metadata_is_compatible_with_tuple_pattern
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_entity_metadata_is_compatible_with_tuple_pattern
  fixtures: []
  markers: []
notes:
  behavior: Tuple pattern specs match price-like units.
  redundancy: Unique pattern spec handling.
  decision_rationale: Keep. Pattern matching is important.
---

# Behavior summary

Tuple pattern specs match compatible unit patterns.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Pattern matching is core.

# Fixtures / setup

None.

# Next actions

None.
