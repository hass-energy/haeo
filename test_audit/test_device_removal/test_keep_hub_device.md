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
  nodeid: tests/test_device_removal.py::test_keep_hub_device
  source_file: tests/test_device_removal.py
  test_class: ''
  test_function: test_keep_hub_device
  fixtures: []
  markers: []
notes:
  behavior: Always keeps the hub device (identifier is entry id only).
  redundancy: Unique hub device behavior.
  decision_rationale: Keep. Hub device must not be removed.
---

# Behavior summary

Ensures hub device is retained regardless of subentry state.

# Redundancy / overlap

No overlap with element device removal tests.

# Decision rationale

Keep. Hub device preservation is required.

# Fixtures / setup

Uses Home Assistant fixtures and mock config entry.

# Next actions

None.
