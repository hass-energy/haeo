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
  nodeid: tests/data/loader/test_sensor_loader.py::test_load_sensors_excludes_unavailable
  source_file: tests/data/loader/test_sensor_loader.py
  test_class: ''
  test_function: test_load_sensors_excludes_unavailable
  fixtures: []
  markers: []
notes:
  behavior: Excludes unavailable or missing sensors from results.
  redundancy: Distinct from base load test.
  decision_rationale: Keep. Filtering is important for robustness.
---

# Behavior summary

Unavailable/missing sensors are excluded from load_sensors output.

# Redundancy / overlap

No overlap with conversion test.

# Decision rationale

Keep. Validates filtering behavior.

# Fixtures / setup

Uses Home Assistant states.

# Next actions

None.
