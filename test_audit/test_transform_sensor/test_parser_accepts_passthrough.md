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
  nodeid: tests/test_transform_sensor.py::test_parser_accepts_passthrough
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_parser_accepts_passthrough
  fixtures: []
  markers: []
notes:
  behavior: Parses passthrough transform type.
  redundancy: Same structure as wrap_forecasts parse.
  decision_rationale: Combine with wrap_forecasts parse into a parametrized test.
---

# Behavior summary

Asserts the parser accepts passthrough as a transform type.

# Redundancy / overlap

Overlaps with wrap_forecasts transform parsing.

# Decision rationale

Combine. Parametrize transform type for simple parse checks.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_parser_accepts_wrap_forecasts`.
