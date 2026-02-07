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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_entity_metadata_is_compatible_with_string_constant
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_entity_metadata_is_compatible_with_string_constant
  fixtures: []
  markers: []
notes:
  behavior: String unit specs match only identical units.
  redundancy: Unique spec type coverage.
  decision_rationale: Keep. Ensures string spec handling.
---

# Behavior summary

String unit specs match identical units and reject mismatches.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Spec handling is core.

# Fixtures / setup

None.

# Next actions

None.
