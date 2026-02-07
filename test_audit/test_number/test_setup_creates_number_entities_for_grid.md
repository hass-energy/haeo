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
  nodeid: tests/test_number.py::test_setup_creates_number_entities_for_grid
  source_file: tests/test_number.py
  test_class: ''
  test_function: test_setup_creates_number_entities_for_grid
  fixtures: []
  markers: []
notes:
  behavior: Creates number entities for grid pricing/power limit fields.
  redundancy: Overlaps with multi-element and optional-field tests; this is the basic creation case.
  decision_rationale: Keep. Validates core grid number entity creation.
---

# Behavior summary

Ensures grid configuration yields number entities for configured fields.

# Redundancy / overlap

Some overlap with optional-field and multi-element tests.

# Decision rationale

Keep. Core behavior.

# Fixtures / setup

Uses Home Assistant fixtures and a grid subentry.

# Next actions

None.
