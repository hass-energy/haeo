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
  nodeid: tests/flows/test_hub_flow.py::test_user_flow_different_presets
  source_file: tests/flows/test_hub_flow.py
  test_class: ''
  test_function: test_user_flow_different_presets
  fixtures: []
  markers: []
notes:
  behavior: Different presets apply correct tier values.
  redundancy: Preset mapping coverage.
  decision_rationale: Keep. Ensures presets map to tiers.
---

# Behavior summary

Preset selection applies expected tier durations and counts.

# Redundancy / overlap

Complementary to preset success test.

# Decision rationale

Keep. Validates preset mapping.

# Fixtures / setup

Uses config flow init/configure.

# Next actions

None.
