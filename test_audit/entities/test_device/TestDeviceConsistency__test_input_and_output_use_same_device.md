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
  nodeid: tests/entities/test_device.py::TestDeviceConsistency::test_input_and_output_use_same_device
  source_file: tests/entities/test_device.py
  test_class: TestDeviceConsistency
  test_function: test_input_and_output_use_same_device
  fixtures: []
  markers: []
notes:
  behavior: Input and output entities resolve to same device.
  redundancy: Regression test for identifier mismatch.
  decision_rationale: Keep. Protects cross-platform device consistency.
---

# Behavior summary

Input and output device creation yields same device.

# Redundancy / overlap

Regression coverage for prior bug.

# Decision rationale

Keep. Prevents identifier divergence.

# Fixtures / setup

Uses grid subentry.

# Next actions

None.
