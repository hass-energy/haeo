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
  nodeid: tests/test_sensor_utils.py::test_get_output_sensors_excludes_other_platforms
  source_file: tests/test_sensor_utils.py
  test_class: ''
  test_function: test_get_output_sensors_excludes_other_platforms
  fixtures: []
  markers: []
notes:
  behavior: Filters out entities that are not on the HAEO sensor platform.
  redundancy: Overlaps with missing-state filtering test; can be parameterized.
  decision_rationale: Combine with missing-state filter test.
---

# Behavior summary

Ensures non-HAEO platform entities are excluded from output sensors.

# Redundancy / overlap

Overlaps with missing-state exclusion; both cover filtering criteria.

# Decision rationale

Combine. Parameterize filter reason.

# Fixtures / setup

Uses Home Assistant fixtures and entity registry.

# Next actions

Consider merging with `test_get_output_sensors_excludes_entities_without_state`.
