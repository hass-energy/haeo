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
  nodeid: tests/elements/battery/test_flow.py::test_build_config_normalizes_connection_target_and_partitions
  source_file: tests/elements/battery/test_flow.py
  test_class: ''
  test_function: test_build_config_normalizes_connection_target_and_partitions
  fixtures: []
  markers: []
notes:
  behavior: Builds config with normalized connection target and partition values.
  redundancy: Battery-specific config build behavior.
  decision_rationale: Keep. Ensures config normalization.
---

# Behavior summary

Connection targets and partition values are normalized in config build.

# Redundancy / overlap

Distinct from user flow tests.

# Decision rationale

Keep. Config normalization is important.

# Fixtures / setup

Uses flow build_config.

# Next actions

None.
