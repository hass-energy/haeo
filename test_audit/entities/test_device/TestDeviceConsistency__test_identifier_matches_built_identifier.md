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
  nodeid: tests/entities/test_device.py::TestDeviceConsistency::test_identifier_matches_built_identifier
  source_file: tests/entities/test_device.py
  test_class: TestDeviceConsistency
  test_function: test_identifier_matches_built_identifier
  fixtures: []
  markers: []
notes:
  behavior: Created device identifiers match build_device_identifier helper.
  redundancy: Helper consistency check.
  decision_rationale: Keep. Ensures helper and device creation align.
---

# Behavior summary

Device identifiers include helper output.

# Redundancy / overlap

Complementary to helper and identifier pattern tests.

# Decision rationale

Keep. Prevents inconsistency.

# Fixtures / setup

Uses battery subentry.

# Next actions

None.
