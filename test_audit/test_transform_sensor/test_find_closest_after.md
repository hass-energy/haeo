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
  nodeid: tests/test_transform_sensor.py::test_find_closest_after
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_find_closest_after
  fixtures: []
  markers: []
notes:
  behavior: Selects the closest later time-of-day when no exact match exists.
  redundancy: Mirrors before-case structure; can be parametrized.
  decision_rationale: Combine with closest-before case for a single parametrized test.
---

# Behavior summary

Chooses the nearest later forecast time-of-day when the target is between entries.

# Redundancy / overlap

Overlaps with closest-before test.

# Decision rationale

Combine. Parametrize expected index for before/after.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_find_closest_before`.
