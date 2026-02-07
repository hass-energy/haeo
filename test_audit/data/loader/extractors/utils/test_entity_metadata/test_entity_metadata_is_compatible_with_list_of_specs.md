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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_entity_metadata_is_compatible_with_list_of_specs
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_entity_metadata_is_compatible_with_list_of_specs
  fixtures: []
  markers: []
notes:
  behavior: List-of-specs matches when any spec is compatible.
  redundancy: Unique list spec handling.
  decision_rationale: Keep. Ensures any-of logic.
---

# Behavior summary

List specs match if any contained spec is compatible.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Any-of spec handling is core.

# Fixtures / setup

None.

# Next actions

None.
