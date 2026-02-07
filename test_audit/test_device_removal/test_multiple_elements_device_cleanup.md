---
status:
  reviewed: true
  decision: remove
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_device_removal.py::test_multiple_elements_device_cleanup
  source_file: tests/test_device_removal.py
  test_class: ''
  test_function: test_multiple_elements_device_cleanup
  fixtures: []
  markers: []
notes:
  behavior: Exercises mixed keep/remove decisions across multiple subentries in one test.
  redundancy: Overlaps with focused keep/remove tests; adds limited extra value.
  decision_rationale: Remove if keeping single-case tests.
---

# Behavior summary

Validates mixed keep/remove outcomes for multiple devices in one test.

# Redundancy / overlap

Redundant with dedicated keep/remove tests.

# Decision rationale

Remove. Prefer focused tests for each case.

# Fixtures / setup

Uses Home Assistant fixtures and multiple mock subentries.

# Next actions

If removed, ensure single-case tests remain for coverage.
