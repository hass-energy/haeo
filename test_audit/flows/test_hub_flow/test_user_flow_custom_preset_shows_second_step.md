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
  nodeid: tests/flows/test_hub_flow.py::test_user_flow_custom_preset_shows_second_step
  source_file: tests/flows/test_hub_flow.py
  test_class: ''
  test_function: test_user_flow_custom_preset_shows_second_step
  fixtures: []
  markers: []
notes:
  behavior: Selecting custom preset opens custom_tiers step.
  redundancy: Core multi-step flow behavior.
  decision_rationale: Keep. Ensures custom flow step appears.
---

# Behavior summary

Custom preset routes to custom tiers form.

# Redundancy / overlap

Complementary to custom tiers create test.

# Decision rationale

Keep. Validates multi-step flow.

# Fixtures / setup

Uses config flow init/configure.

# Next actions

None.
