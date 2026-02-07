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
  nodeid: tests/test_device_removal.py::test_keep_device_for_existing_element
  source_file: tests/test_device_removal.py
  test_class: ''
  test_function: test_keep_device_for_existing_element
  fixtures: []
  markers: []
notes:
  behavior: Keeps devices associated with existing subentries.
  redundancy: Baseline case; overlaps with multi-element cleanup but clearer.
  decision_rationale: Keep. Simple baseline for existing elements.
---

# Behavior summary

Asserts device removal returns False when the subentry exists.

# Redundancy / overlap

Overlaps with multi-element cleanup but provides a focused baseline.

# Decision rationale

Keep. Baseline coverage for existing element devices.

# Fixtures / setup

Uses Home Assistant fixtures and mock config entries.

# Next actions

None.
