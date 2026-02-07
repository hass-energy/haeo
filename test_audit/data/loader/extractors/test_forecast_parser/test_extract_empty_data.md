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
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::test_extract_empty_data
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: ''
  test_function: test_extract_empty_data
  fixtures: []
  markers: []
notes:
  behavior: Empty attributes fall back to simple float extraction.
  redundancy: Related to unknown-format fallback tests.
  decision_rationale: Keep. Empty attributes are a distinct case.
---

# Behavior summary

Empty attributes are parsed as simple numeric values.

# Redundancy / overlap

Adjacent to unknown-format fallback behavior but distinct input.

# Decision rationale

Keep. Empty attribute fallback should be explicit.

# Fixtures / setup

Uses Home Assistant state fixture.

# Next actions

None.
