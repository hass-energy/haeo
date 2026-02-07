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
  nodeid: tests/data/loader/extractors/utils/test_entity_metadata.py::test_extract_entity_metadata_filters_domain
  source_file: tests/data/loader/extractors/utils/test_entity_metadata.py
  test_class: ''
  test_function: test_extract_entity_metadata_filters_domain
  fixtures: []
  markers: []
notes:
  behavior: Extracts metadata only for sensor and input_number domains.
  redundancy: Unique domain filtering coverage.
  decision_rationale: Keep. Domain filtering is important.
---

# Behavior summary

Only sensor and input_number entities are included in metadata extraction.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures domain filtering.

# Fixtures / setup

Uses entity registry fixtures.

# Next actions

None.
