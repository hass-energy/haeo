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
  nodeid: tests/entities/test_device.py::TestGetOrCreateElementDevice::test_same_device_returned_on_subsequent_calls
  source_file: tests/entities/test_device.py
  test_class: TestGetOrCreateElementDevice
  test_function: test_same_device_returned_on_subsequent_calls
  fixtures: []
  markers: []
notes:
  behavior: Repeated calls return same device for element.
  redundancy: Core caching behavior.
  decision_rationale: Keep. Ensures device reuse.
---

# Behavior summary

Element device creation is idempotent.

# Redundancy / overlap

Distinct from identifier pattern tests.

# Decision rationale

Keep. Prevents duplicate device creation.

# Fixtures / setup

Uses mock config entry and subentry.

# Next actions

None.
