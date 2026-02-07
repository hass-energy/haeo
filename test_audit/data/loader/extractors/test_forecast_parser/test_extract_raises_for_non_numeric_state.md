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
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::test_extract_raises_for_non_numeric_state
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: ''
  test_function: test_extract_raises_for_non_numeric_state
  fixtures: []
  markers: []
notes:
  behavior: Non-numeric states raise ValueError during fallback extraction.
  redundancy: Unique error path.
  decision_rationale: Keep. Ensures clear errors for invalid state.
---

# Behavior summary

Non-numeric state values raise ValueError.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures proper error handling.

# Fixtures / setup

Uses Home Assistant state fixture.

# Next actions

None.
