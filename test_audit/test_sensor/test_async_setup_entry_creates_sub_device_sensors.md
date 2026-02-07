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
  nodeid: tests/test_sensor.py::test_async_setup_entry_creates_sub_device_sensors
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_async_setup_entry_creates_sub_device_sensors
  fixtures: []
  markers: []
notes:
  behavior: Creates sensors for sub-devices and validates translation/device metadata.
  redundancy: Distinct coverage for sub-device sensor creation.
  decision_rationale: Keep. Sub-device sensors are important.
---

# Behavior summary

Ensures sub-device sensors are created with proper translation key and device association.

# Redundancy / overlap

No overlap with general sensor setup tests.

# Decision rationale

Keep. Sub-device handling is distinct.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator data.

# Next actions

None.
