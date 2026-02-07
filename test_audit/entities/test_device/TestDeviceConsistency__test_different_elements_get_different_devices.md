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
  nodeid: tests/entities/test_device.py::TestDeviceConsistency::test_different_elements_get_different_devices
  source_file: tests/entities/test_device.py
  test_class: TestDeviceConsistency
  test_function: test_different_elements_get_different_devices
  fixtures: []
  markers: []
notes:
  behavior: Different element subentries map to distinct devices.
  redundancy: Core device segregation behavior.
  decision_rationale: Keep. Ensures device separation.
---

# Behavior summary

Different elements produce different devices.

# Redundancy / overlap

Distinct from network separation test.

# Decision rationale

Keep. Prevents device collisions.

# Fixtures / setup

Uses battery and grid subentries.

# Next actions

None.
