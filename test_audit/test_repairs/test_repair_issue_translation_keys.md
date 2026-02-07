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
  nodeid: tests/test_repairs.py::test_repair_issue_translation_keys
  source_file: tests/test_repairs.py
  test_class: ''
  test_function: test_repair_issue_translation_keys
  fixtures: []
  markers: []
notes:
  behavior: Verifies translation keys for missing sensor, optimization failure, and invalid config issues.
  redundancy: Overlaps with issue creation tests but focuses on translation keys.
  decision_rationale: Keep. Translation keys should be validated.
---

# Behavior summary

Ensures repair issues have expected translation keys.

# Redundancy / overlap

Overlap with issue creation tests but covers translation keys specifically.

# Decision rationale

Keep. Translation keys are critical for UI messages.

# Fixtures / setup

Uses Home Assistant fixtures and issue registry.

# Next actions

None.
