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
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::TestInterpolationModeExtraction::test_previous_mode_adds_synthetic_points
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: TestInterpolationModeExtraction
  test_function: test_previous_mode_adds_synthetic_points
  fixtures: []
  markers: []
notes:
  behavior: Previous mode adds synthetic points for step behavior.
  redundancy: Distinct interpolation mode.
  decision_rationale: Keep. Mode-specific behavior.
---

# Behavior summary

Previous interpolation adds a synthetic point to create step behavior.

# Redundancy / overlap

No overlap with other modes.

# Decision rationale

Keep. Mode-specific behavior should be validated.

# Fixtures / setup

Uses forecast state with interpolation_mode set to previous.

# Next actions

None.
