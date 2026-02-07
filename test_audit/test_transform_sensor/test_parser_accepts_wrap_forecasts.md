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
  nodeid: tests/test_transform_sensor.py::test_parser_accepts_wrap_forecasts
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_parser_accepts_wrap_forecasts
  fixtures: []
  markers: []
notes:
  behavior: Parses wrap_forecasts transform type.
  redundancy: Same structure as passthrough transform parse.
  decision_rationale: Combine with passthrough parse into a parametrized test.
---

# Behavior summary

Asserts the parser accepts wrap_forecasts as a transform type.

# Redundancy / overlap

Overlaps with passthrough transform parsing.

# Decision rationale

Combine. Parametrize transform type for simple parse checks.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_parser_accepts_passthrough`.
