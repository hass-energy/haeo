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
  nodeid: tests/data/loader/test_sensor_loader.py::test_load_sensors_returns_mapping
  source_file: tests/data/loader/test_sensor_loader.py
  test_class: ''
  test_function: test_load_sensors_returns_mapping
  fixtures: []
  markers: []
notes:
  behavior: Loads multiple sensors, converts units, returns float payloads.
  redundancy: Unique multi-sensor load behavior.
  decision_rationale: Keep. Confirms unit conversion in bulk load.
---

# Behavior summary

Load_sensors returns float payloads with unit conversion.

# Redundancy / overlap

No overlap with exclusion test.

# Decision rationale

Keep. Ensures multi-sensor load behavior.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
