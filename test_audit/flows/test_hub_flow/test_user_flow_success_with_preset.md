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
  nodeid: tests/flows/test_hub_flow.py::test_user_flow_success_with_preset
  source_file: tests/flows/test_hub_flow.py
  test_class: ''
  test_function: test_user_flow_success_with_preset
  fixtures: []
  markers: []
notes:
  behavior: User flow with preset creates hub entry and applies preset tiers.
  redundancy: Core hub creation behavior.
  decision_rationale: Keep. Ensures preset flow works.
---

# Behavior summary

Preset selection creates entry with preset tier values.

# Redundancy / overlap

Complementary to custom preset tests.

# Decision rationale

Keep. Validates main flow path.

# Fixtures / setup

Uses config flow init/configure.

# Next actions

None.
