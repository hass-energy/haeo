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
  nodeid: tests/test_device_removal.py::test_remove_device_with_unrelated_haeo_identifier
  source_file: tests/test_device_removal.py
  test_class: ''
  test_function: test_remove_device_with_unrelated_haeo_identifier
  fixtures: []
  markers: []
notes:
  behavior: Removes HAEO-domain devices with unrelated identifiers.
  redundancy: Unique case for unrelated HAEO identifiers.
  decision_rationale: Keep. Ensures unrelated devices are cleaned up.
---

# Behavior summary

Asserts devices with unrelated HAEO identifiers are removed.

# Redundancy / overlap

No overlap with existing/deleted element cases.

# Decision rationale

Keep. Ensures cleanup of unrelated HAEO devices.

# Fixtures / setup

Uses Home Assistant fixtures and mock identifiers.

# Next actions

None.
