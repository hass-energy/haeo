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
  nodeid: tests/test_transform_sensor.py::test_parse_forecasts_sorted_by_time
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_parse_forecasts_sorted_by_time
  fixtures: []
  markers: []
notes:
  behavior: Ensures parsed forecasts are sorted chronologically.
  redundancy: Unique ordering behavior.
  decision_rationale: Keep. Sorting is a distinct requirement.
---

# Behavior summary

Verifies that parsed forecast entries are returned in ascending time order.

# Redundancy / overlap

No overlap with parse success or error cases.

# Decision rationale

Keep. Sorting is a separate behavior.

# Fixtures / setup

None.

# Next actions

None.
