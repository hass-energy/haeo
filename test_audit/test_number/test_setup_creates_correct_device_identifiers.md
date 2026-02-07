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
  nodeid: tests/test_number.py::test_setup_creates_correct_device_identifiers
  source_file: tests/test_number.py
  test_class: ''
  test_function: test_setup_creates_correct_device_identifiers
  fixtures: []
  markers: []
notes:
  behavior: Ensures number entities include device identifiers.
  redundancy: Distinct device metadata check.
  decision_rationale: Keep. Device linkage is important.
---

# Behavior summary

Asserts created number entities are associated with a device entry.

# Redundancy / overlap

Could be folded into entity creation tests but adds explicit metadata validation.

# Decision rationale

Keep. Device metadata should be validated.

# Fixtures / setup

Uses Home Assistant fixtures and a grid subentry.

# Next actions

None.
