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
  nodeid: tests/test_number.py::test_setup_skips_missing_fields_in_config
  source_file: tests/test_number.py
  test_class: ''
  test_function: test_setup_skips_missing_fields_in_config
  fixtures: []
  markers: []
notes:
  behavior: Only configured fields create entities; optional fields missing are skipped.
  redundancy: Complement to basic creation test; adds optional-field coverage.
  decision_rationale: Keep. Validates optional field handling.
---

# Behavior summary

Asserts only present fields generate entities when optional fields are absent.

# Redundancy / overlap

Some overlap with basic creation test but covers optional field behavior.

# Decision rationale

Keep. Optional fields need explicit coverage.

# Fixtures / setup

Uses Home Assistant fixtures and a grid subentry.

# Next actions

None.
