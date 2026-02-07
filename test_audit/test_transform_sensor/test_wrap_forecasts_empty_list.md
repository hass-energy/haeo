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
  nodeid: tests/test_transform_sensor.py::test_wrap_forecasts_empty_list
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_wrap_forecasts_empty_list
  fixtures: []
  markers: []
notes:
  behavior: Returns input unchanged when forecasts list is empty.
  redundancy: Outcome overlaps with missing attributes; candidate for parametrization.
  decision_rationale: Combine with missing attributes case if reducing tests.
---

# Behavior summary

Empty forecast lists result in the input data being returned unchanged.

# Redundancy / overlap

Overlaps with missing-attributes behavior.

# Decision rationale

Combine. Could parametrize missing/empty input conditions.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_wrap_forecasts_missing_attributes`.
