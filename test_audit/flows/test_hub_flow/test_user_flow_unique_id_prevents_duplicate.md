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
  nodeid: tests/flows/test_hub_flow.py::test_user_flow_unique_id_prevents_duplicate
  source_file: tests/flows/test_hub_flow.py
  test_class: ''
  test_function: test_user_flow_unique_id_prevents_duplicate
  fixtures: []
  markers: []
notes:
  behavior: Unique ID prevents duplicate hub entries.
  redundancy: Uniqueness enforcement coverage.
  decision_rationale: Keep. Ensures unique ID gating.
---

# Behavior summary

Duplicate unique IDs abort flow.

# Redundancy / overlap

Distinct from name duplicate validation.

# Decision rationale

Keep. Prevents duplicate hub entries.

# Fixtures / setup

Uses config entry with unique ID.

# Next actions

None.
