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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_entity_metadata_is_compatible_with_none_unit
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_entity_metadata_is_compatible_with_none_unit
  fixtures: []
  markers: []
notes:
  behavior: None units are never compatible with any spec.
  redundancy: Unique edge case.
  decision_rationale: Keep. Ensures None handling.
---

# Behavior summary

None unit never matches compatibility specs.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Validates None handling.

# Fixtures / setup

None.

# Next actions

None.
