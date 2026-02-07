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
  nodeid: tests/elements/connection/test_flow.py::test_build_config_normalizes_endpoints
  source_file: tests/elements/connection/test_flow.py
  test_class: ''
  test_function: test_build_config_normalizes_endpoints
  fixtures: []
  markers: []
notes:
  behavior: Builds config with normalized endpoints for connections.
  redundancy: Connection-specific behavior.
  decision_rationale: Keep. Endpoint normalization is critical.
---

# Behavior summary

Connection config normalizes endpoints into connection targets.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures endpoint normalization.

# Fixtures / setup

Uses flow build_config.

# Next actions

None.
