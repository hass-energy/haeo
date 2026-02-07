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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_extract_entity_metadata_includes_none_unit
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_extract_entity_metadata_includes_none_unit
  fixtures: []
  markers: []
notes:
  behavior: Includes entities without units for exclusion mask usage.
  redundancy: Unique behavior for unit-less entities.
  decision_rationale: Keep. Unit-less entities should be accounted for.
---

# Behavior summary

Entities without units are included in metadata extraction.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures unit-less entities are included.

# Fixtures / setup

Uses entity registry fixtures.

# Next actions

None.
