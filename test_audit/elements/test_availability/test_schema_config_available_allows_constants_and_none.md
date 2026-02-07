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
  nodeid: tests/elements/test_availability.py::test_schema_config_available_allows_constants_and_none
  source_file: tests/elements/test_availability.py
  test_class: ''
  test_function: test_schema_config_available_allows_constants_and_none
  fixtures: []
  markers: []
notes:
  behavior: Ignores constant, none, and connection target values during availability checks.
  redundancy: Unique to availability helper.
  decision_rationale: Keep. Ensures non-entity values don't block availability.
---

# Behavior summary

Availability ignores constant, none, and connection target values.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Core availability behavior.

# Fixtures / setup

Uses Home Assistant fixture.

# Next actions

None.
