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
  nodeid: tests/schema/test_util.py::test_matches_unit_spec
  source_file: tests/schema/test_util.py
  test_class: ''
  test_function: test_matches_unit_spec
  fixtures: []
  markers: []
notes:
  behavior: Validates unit spec matching across power, energy, and price formats.
  redundancy: Complements currency pattern tests.
  decision_rationale: Keep. Core unit-matching behavior should be stable.
---

# Behavior summary

Validates unit spec matching for supported unit patterns and aliases.

# Redundancy / overlap

Distinct from currency-only pattern tests.

# Decision rationale

Keep. Ensures unit matching stays correct.

# Fixtures / setup

None.

# Next actions

None.
