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
  nodeid: tests/elements/battery/test_adapter.py::test_discharge_respects_power_limit_with_efficiency
  source_file: tests/elements/battery/test_adapter.py
  test_class: ''
  test_function: test_discharge_respects_power_limit_with_efficiency
  fixtures: []
  markers: []
notes:
  behavior: Network optimization respects discharge power limit with efficiency segment.
  redundancy: Unique integration-level solver behavior.
  decision_rationale: Keep. Ensures solver respects power limits.
---

# Behavior summary

Discharge is capped at the configured power limit despite efficiency.

# Redundancy / overlap

Distinct from charge-limit test.

# Decision rationale

Keep. Discharge limit is critical.

# Fixtures / setup

Uses model Network and optimization.

# Next actions

None.
