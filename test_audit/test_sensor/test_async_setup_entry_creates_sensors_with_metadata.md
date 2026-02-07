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
  nodeid: tests/test_sensor.py::test_async_setup_entry_creates_sensors_with_metadata
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_async_setup_entry_creates_sensors_with_metadata
  fixtures: []
  markers: []
notes:
  behavior: Creates horizon/output sensors and applies metadata such as device class, state class, and units.
  redundancy: Some overlap with horizon-only test but adds metadata assertions.
  decision_rationale: Keep. Validates core sensor setup and metadata wiring.
---

# Behavior summary

Ensures sensor setup creates output sensors with expected metadata and values.

# Redundancy / overlap

Partial overlap with horizon-only setup test.

# Decision rationale

Keep. This is the main setup verification.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator data.

# Next actions

None.
