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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_entity_metadata_is_compatible_with_enum
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_entity_metadata_is_compatible_with_enum
  fixtures: []
  markers: []
notes:
  behavior: Enum unit specs match only compatible units.
  redundancy: Unique spec type coverage.
  decision_rationale: Keep. Ensures enum spec handling.
---

# Behavior summary

Enum-based unit specs match compatible units and reject incompatible ones.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Spec handling is core.

# Fixtures / setup

None.

# Next actions

None.
