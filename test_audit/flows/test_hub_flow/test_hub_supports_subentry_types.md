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
  nodeid: tests/flows/test_hub_flow.py::test_hub_supports_subentry_types
  source_file: tests/flows/test_hub_flow.py
  test_class: ''
  test_function: test_hub_supports_subentry_types
  fixtures: []
  markers: []
notes:
  behavior: Hub flow supports all configured subentry types.
  redundancy: Registry coverage.
  decision_rationale: Keep. Ensures hub supports element subentries.
---

# Behavior summary

Hub flow advertises all element subentry types.

# Redundancy / overlap

Distinct from translations test.

# Decision rationale

Keep. Prevents missing subentry types.

# Fixtures / setup

Uses element registry.

# Next actions

None.
