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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_entity_metadata_is_compatible_with_list_of_patterns
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_entity_metadata_is_compatible_with_list_of_patterns
  fixtures: []
  markers: []
notes:
  behavior: List of pattern specs matches if any pattern is compatible.
  redundancy: Unique list-of-patterns handling.
  decision_rationale: Keep. Pattern matching is core.
---

# Behavior summary

Pattern list matches if any pattern is compatible.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Pattern list handling is important.

# Fixtures / setup

None.

# Next actions

None.
