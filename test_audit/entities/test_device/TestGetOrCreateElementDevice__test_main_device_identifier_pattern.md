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
  nodeid: tests/entities/test_device.py::TestGetOrCreateElementDevice::test_main_device_identifier_pattern
  source_file: tests/entities/test_device.py
  test_class: TestGetOrCreateElementDevice
  test_function: test_main_device_identifier_pattern
  fixtures: []
  markers: []
notes:
  behavior: Element devices use entry/subentry/device name identifier pattern.
  redundancy: Core device identity behavior.
  decision_rationale: Keep. Ensures consistent device identifiers.
---

# Behavior summary

Builds element device identifiers with entry and subentry IDs.

# Redundancy / overlap

Complementary to build_device_identifier tests.

# Decision rationale

Keep. Prevents identifier regressions.

# Fixtures / setup

Uses mock config entry and subentry.

# Next actions

None.
