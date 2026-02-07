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
  nodeid: tests/elements/battery/test_adapter.py::test_charge_respects_power_limit_with_efficiency
  source_file: tests/elements/battery/test_adapter.py
  test_class: ''
  test_function: test_charge_respects_power_limit_with_efficiency
  fixtures: []
  markers: []
notes:
  behavior: Network optimization respects charge power limit with efficiency segment.
  redundancy: Distinct from discharge-limit test.
  decision_rationale: Keep. Ensures solver respects charge limits.
---

# Behavior summary

Charge is capped at the configured power limit despite efficiency.

# Redundancy / overlap

Distinct from discharge-limit test.

# Decision rationale

Keep. Charge limit is critical.

# Fixtures / setup

Uses model Network and optimization.

# Next actions

None.
