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
  nodeid: tests/test_switch.py::test_setup_creates_switch_entities_for_solar_curtailment
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_setup_creates_switch_entities_for_solar_curtailment
  fixtures: []
  markers: []
notes:
  behavior: Creates a solar curtailment switch when configured.
  redundancy: Related to missing-switch-field and driven-mode cases; this is the main creation path.
  decision_rationale: Keep. Validates switch creation for curtailment.
---

# Behavior summary

Verifies solar curtailment configuration produces a switch entity.

# Redundancy / overlap

Some overlap with missing-field and driven-mode tests.

# Decision rationale

Keep. Primary coverage for curtailment switch creation.

# Fixtures / setup

Uses Home Assistant fixtures and mock solar subentry.

# Next actions

If consolidating, parametrize with missing/driven cases.
