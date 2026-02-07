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
  nodeid: tests/elements/connection/test_flow.py::test_flow_source_equals_target_error
  source_file: tests/elements/connection/test_flow.py
  test_class: ''
  test_function: test_flow_source_equals_target_error
  fixtures: []
  markers: []
notes:
  behavior: User flow rejects connections with identical source and target.
  redundancy: Connection-specific validation.
  decision_rationale: Keep. Source/target validation is critical.
---

# Behavior summary

User flow blocks source == target connections.

# Redundancy / overlap

Distinct from reconfigure validation test.

# Decision rationale

Keep. Connection validity must be enforced.

# Fixtures / setup

Uses hub entry and participant setup.

# Next actions

None.
