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
  nodeid: tests/test_diagnostics.py::test_extract_entity_ids_from_config_collects_nested_entities
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_extract_entity_ids_from_config_collects_nested_entities
  fixtures: []
  markers: []
notes:
  behavior: Collects valid entity IDs from nested config and ignores constants/invalid IDs.
  redundancy: Unique coverage for entity ID extraction.
  decision_rationale: Keep. Validates config scanning behavior.
---

# Behavior summary

Ensures entity IDs are extracted correctly from nested config structures.

# Redundancy / overlap

No overlap with diagnostics collection tests.

# Decision rationale

Keep. Entity ID extraction is foundational.

# Fixtures / setup

None.

# Next actions

None.
