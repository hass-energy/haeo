---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::test_extract_unknown_format_falls_back_to_simple_value
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: ''
  test_function: test_extract_unknown_format_falls_back_to_simple_value
  fixtures: []
  markers: []
notes:
  behavior: Unknown attributes fall back to simple value extraction.
  redundancy: Overlaps with unknown-format unit test and empty-attributes fallback.
  decision_rationale: Combine with unit-return or empty-attributes tests.
---

# Behavior summary

Unknown formats fall back to numeric state extraction.

# Redundancy / overlap

Overlaps with unknown-format unit test.

# Decision rationale

Combine. Reduces duplication.

# Fixtures / setup

Uses Home Assistant state fixture.

# Next actions

Consider merging with unit-return test.
