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
  nodeid: tests/entities/test_device.py::TestDeviceConsistency::test_network_device_separate_from_element_devices
  source_file: tests/entities/test_device.py
  test_class: TestDeviceConsistency
  test_function: test_network_device_separate_from_element_devices
  fixtures: []
  markers: []
notes:
  behavior: Network device is distinct from element devices.
  redundancy: Core separation behavior.
  decision_rationale: Keep. Ensures network is separate device.
---

# Behavior summary

Network and element devices are different entries.

# Redundancy / overlap

Distinct from different-element device test.

# Decision rationale

Keep. Prevents device conflation.

# Fixtures / setup

Uses network and battery subentries.

# Next actions

None.
