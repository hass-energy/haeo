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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_extract_entity_metadata_uses_get_extracted_units
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_extract_entity_metadata_uses_get_extracted_units
  fixtures: []
  markers: []
notes:
  behavior: Uses extracted units for forecast-aware entities.
  redundancy: Unique extraction path.
  decision_rationale: Keep. Ensures unit extraction is used.
---

# Behavior summary

Extracted units are used for metadata when available.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures unit extraction path is exercised.

# Fixtures / setup

Uses entity registry fixtures.

# Next actions

None.
