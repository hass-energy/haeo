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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_extract_entity_metadata_skips_none_state
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_extract_entity_metadata_skips_none_state
  fixtures: []
  markers: []
notes:
  behavior: Skips entities with None state when extracting metadata.
  redundancy: Unique edge case.
  decision_rationale: Keep. Prevents invalid metadata entries.
---

# Behavior summary

Entities without state are excluded from metadata extraction.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures correct filtering.

# Fixtures / setup

Uses entity registry fixtures.

# Next actions

None.
