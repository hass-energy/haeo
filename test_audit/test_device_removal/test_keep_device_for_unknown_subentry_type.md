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
  nodeid: tests/test_device_removal.py::test_keep_device_for_unknown_subentry_type
  source_file: tests/test_device_removal.py
  test_class: ''
  test_function: test_keep_device_for_unknown_subentry_type
  fixtures: []
  markers: []
notes:
  behavior: Keeps devices for unknown subentry types to avoid accidental removal.
  redundancy: Unique safety case for unknown types.
  decision_rationale: Keep. Conservative behavior is required.
---

# Behavior summary

Ensures devices tied to unknown subentry types are preserved.

# Redundancy / overlap

No overlap with standard element cases.

# Decision rationale

Keep. Unknown types should not be removed.

# Fixtures / setup

Uses Home Assistant fixtures and mock device identifiers.

# Next actions

None.
