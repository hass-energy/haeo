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
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::TestInterpolationModeExtraction::test_simple_value_ignores_interpolation_mode
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: TestInterpolationModeExtraction
  test_function: test_simple_value_ignores_interpolation_mode
  fixtures: []
  markers: []
notes:
  behavior: Interpolation mode is ignored for simple (non-forecast) values.
  redundancy: Distinct cross-path behavior.
  decision_rationale: Keep. Ensures non-forecast values ignore mode.
---

# Behavior summary

Simple values ignore interpolation_mode settings.

# Redundancy / overlap

No overlap with forecast mode tests.

# Decision rationale

Keep. Ensures correct handling of simple values.

# Fixtures / setup

Uses simple-value state with interpolation_mode set.

# Next actions

None.
