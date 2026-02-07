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
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::test_extract_unknown_format_returns_unit
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: ''
  test_function: test_extract_unknown_format_returns_unit
  fixtures: []
  markers: []
notes:
  behavior: Unknown formats return simple value plus sensor unit.
  redundancy: Related to unknown-format fallback test.
  decision_rationale: Keep. Unit propagation is important.
---

# Behavior summary

Unknown formats return numeric value with unit preserved.

# Redundancy / overlap

Overlaps with fallback test but adds unit assertion.

# Decision rationale

Keep. Unit propagation is a distinct requirement.

# Fixtures / setup

Uses direct State object.

# Next actions

None.
