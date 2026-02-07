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
  nodeid: tests/entities/test_device.py::TestGetOrCreateNetworkDevice::test_network_device_identifier_pattern
  source_file: tests/entities/test_device.py
  test_class: TestGetOrCreateNetworkDevice
  test_function: test_network_device_identifier_pattern
  fixtures: []
  markers: []
notes:
  behavior: Network device identifiers use entry/subentry/network pattern.
  redundancy: Core network device identity behavior.
  decision_rationale: Keep. Ensures network identifiers are correct.
---

# Behavior summary

Builds network device identifiers with entry and subentry IDs.

# Redundancy / overlap

Distinct from element device identifier tests.

# Decision rationale

Keep. Prevents identifier regressions.

# Fixtures / setup

Uses network subentry.

# Next actions

None.
