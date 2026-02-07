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
  nodeid: tests/test_transform_sensor.py::test_find_exact_match
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_find_exact_match
  fixtures: []
  markers: []
notes:
  behavior: Returns the index of an exact time-of-day match.
  redundancy: Distinct from before/after nearest-match cases.
  decision_rationale: Keep. Exact match handling is a separate branch.
---

# Behavior summary

Uses a forecast time matching the target time-of-day and asserts the exact index is returned.

# Redundancy / overlap

No overlap with nearest-before/after cases.

# Decision rationale

Keep. Ensures exact-match branch works.

# Fixtures / setup

None.

# Next actions

None.
