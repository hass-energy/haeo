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
  nodeid: tests/flows/test_hub_flow.py::test_user_flow_duplicate_name
  source_file: tests/flows/test_hub_flow.py
  test_class: ''
  test_function: test_user_flow_duplicate_name
  fixtures: []
  markers: []
notes:
  behavior: User flow rejects duplicate hub name.
  redundancy: Validation coverage.
  decision_rationale: Keep. Ensures duplicate detection.
---

# Behavior summary

Duplicate hub names produce validation errors.

# Redundancy / overlap

Distinct from element duplicate tests.

# Decision rationale

Keep. Prevents duplicate hubs.

# Fixtures / setup

Uses existing config entry.

# Next actions

None.
