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
  nodeid: tests/flows/test_hub_flow.py::test_user_flow_custom_tiers_creates_entry
  source_file: tests/flows/test_hub_flow.py
  test_class: ''
  test_function: test_user_flow_custom_tiers_creates_entry
  fixtures: []
  markers: []
notes:
  behavior: Custom tiers step creates entry with custom tier values.
  redundancy: Core custom tier flow behavior.
  decision_rationale: Keep. Ensures custom tiers are saved.
---

# Behavior summary

Custom tiers values persist and entry is created.

# Redundancy / overlap

Complementary to custom preset step test.

# Decision rationale

Keep. Validates custom flow path.

# Fixtures / setup

Uses two-step config flow.

# Next actions

None.
