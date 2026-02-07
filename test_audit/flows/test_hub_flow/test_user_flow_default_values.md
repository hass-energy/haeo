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
  nodeid: tests/flows/test_hub_flow.py::test_user_flow_default_values
  source_file: tests/flows/test_hub_flow.py
  test_class: ''
  test_function: test_user_flow_default_values
  fixtures: []
  markers: []
notes:
  behavior: Default hub flow values are applied when omitted.
  redundancy: Default value coverage.
  decision_rationale: Keep. Ensures defaults are applied.
---

# Behavior summary

Default tier and debounce values are applied.

# Redundancy / overlap

Complementary to preset/custom tests.

# Decision rationale

Keep. Validates defaults.

# Fixtures / setup

Uses flow with minimal input.

# Next actions

None.
