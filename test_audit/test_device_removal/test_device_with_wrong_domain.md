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
  nodeid: tests/test_device_removal.py::test_device_with_wrong_domain
  source_file: tests/test_device_removal.py
  test_class: ''
  test_function: test_device_with_wrong_domain
  fixtures: []
  markers: []
notes:
  behavior: Keeps devices that belong to a different domain.
  redundancy: Unique cross-domain safety case.
  decision_rationale: Keep. Avoids removing non-HAEO devices.
---

# Behavior summary

Asserts devices with non-HAEO identifiers are not removed.

# Redundancy / overlap

No overlap with HAEO device removal cases.

# Decision rationale

Keep. Cross-domain safety is required.

# Fixtures / setup

Uses Home Assistant fixtures and mock device identifiers.

# Next actions

None.
