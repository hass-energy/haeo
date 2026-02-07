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
  nodeid: tests/entities/test_device.py::TestBuildDeviceIdentifier::test_main_device_identifier
  source_file: tests/entities/test_device.py
  test_class: TestBuildDeviceIdentifier
  test_function: test_main_device_identifier
  fixtures: []
  markers: []
notes:
  behavior: build_device_identifier returns expected identifier tuple.
  redundancy: Core helper behavior.
  decision_rationale: Keep. Ensures identifier helper matches device creation.
---

# Behavior summary

Helper builds identifier tuple with entry and subentry IDs.

# Redundancy / overlap

Supports device creation tests.

# Decision rationale

Keep. Prevents helper regressions.

# Fixtures / setup

Uses mock entry and subentry.

# Next actions

None.
