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
  nodeid: tests/elements/grid/test_adapter.py::test_available_returns_false_when_import_price_missing
  source_file: tests/elements/grid/test_adapter.py
  test_class: ''
  test_function: test_available_returns_false_when_import_price_missing
  fixtures: []
  markers: []
notes:
  behavior: Availability fails when import price sensor is missing.
  redundancy: Missing-sensor guard.
  decision_rationale: Keep. Required sensors must be enforced.
---

# Behavior summary

Missing import price sensor makes availability false.

# Redundancy / overlap

Distinct from export-missing case.

# Decision rationale

Keep. Availability guard is important.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.
