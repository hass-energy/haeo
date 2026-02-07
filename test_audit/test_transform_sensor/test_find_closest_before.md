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
  nodeid: tests/test_transform_sensor.py::test_find_closest_before
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_find_closest_before
  fixtures: []
  markers: []
notes:
  behavior: Selects the closest earlier time-of-day when no exact match exists.
  redundancy: Mirrors after-case structure; can be parametrized.
  decision_rationale: Combine with closest-after case for a single parametrized test.
---

# Behavior summary

Chooses the nearest earlier forecast time-of-day when the target is between two entries.

# Redundancy / overlap

Overlaps with closest-after test; same data setup.

# Decision rationale

Combine. Parametrize expected index for before/after.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_find_closest_after`.
