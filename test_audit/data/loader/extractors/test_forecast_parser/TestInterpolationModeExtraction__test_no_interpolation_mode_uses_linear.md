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
  nodeid: tests/data/loader/extractors/test_forecast_parser.py::TestInterpolationModeExtraction::test_no_interpolation_mode_uses_linear
  source_file: tests/data/loader/extractors/test_forecast_parser.py
  test_class: TestInterpolationModeExtraction
  test_function: test_no_interpolation_mode_uses_linear
  fixtures: []
  markers: []
notes:
  behavior: No interpolation_mode defaults to linear behavior.
  redundancy: Overlaps with explicit linear mode test.
  decision_rationale: Combine with explicit linear mode test.
---

# Behavior summary

Missing interpolation_mode defaults to linear behavior.

# Redundancy / overlap

Overlaps with explicit linear mode test.

# Decision rationale

Combine with explicit linear test.

# Fixtures / setup

Uses forecast state with no interpolation_mode.

# Next actions

Consider parameterizing with explicit linear test.
