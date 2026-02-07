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
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::TestInterpolationModeExtraction::test_invalid_mode_falls_back_to_linear
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: TestInterpolationModeExtraction
  test_function: test_invalid_mode_falls_back_to_linear
  fixtures: []
  markers: []
notes:
  behavior: Invalid interpolation_mode falls back to linear behavior.
  redundancy: Distinct invalid-mode handling.
  decision_rationale: Keep. Ensures fallback behavior.
---

# Behavior summary

Invalid interpolation modes revert to linear behavior.

# Redundancy / overlap

No overlap with other modes.

# Decision rationale

Keep. Fallback behavior is important.

# Fixtures / setup

Uses forecast state with invalid interpolation_mode.

# Next actions

None.
