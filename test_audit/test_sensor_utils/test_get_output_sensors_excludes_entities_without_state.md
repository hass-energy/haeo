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
  nodeid: tests/test_sensor_utils.py::test_get_output_sensors_excludes_entities_without_state
  source_file: tests/test_sensor_utils.py
  test_class: ''
  test_function: test_get_output_sensors_excludes_entities_without_state
  fixtures: []
  markers: []
notes:
  behavior: Excludes HAEO entities that have no state set.
  redundancy: Overlaps with platform exclusion test; can be parameterized.
  decision_rationale: Combine with platform exclusion test.
---

# Behavior summary

Ensures entities without state are filtered out of output sensors.

# Redundancy / overlap

Overlaps with platform exclusion test.

# Decision rationale

Combine. Parameterize filter reason.

# Fixtures / setup

Uses Home Assistant fixtures and entity registry.

# Next actions

Consider merging with `test_get_output_sensors_excludes_other_platforms`.
