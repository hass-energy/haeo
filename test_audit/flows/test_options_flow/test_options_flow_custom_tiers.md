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
  nodeid: tests/flows/test_options_flow.py::test_options_flow_custom_tiers
  source_file: tests/flows/test_options_flow.py
  test_class: ''
  test_function: test_options_flow_custom_tiers
  fixtures: []
  markers: []
notes:
  behavior: Custom preset opens custom tiers step and applies values.
  redundancy: Core options custom tiers behavior.
  decision_rationale: Keep. Ensures custom tiers path works.
---

# Behavior summary

Custom preset routes to custom tiers step and saves values.

# Redundancy / overlap

Complementary to preset options test.

# Decision rationale

Keep. Validates custom tiers options flow.

# Fixtures / setup

Uses options flow configure.

# Next actions

None.
