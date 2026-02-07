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
  nodeid: tests/migrations/test_v1_3.py::test_migrate_subentry_load_node_solar
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_migrate_subentry_load_node_solar
  fixtures: []
  markers: []
notes:
  behavior: Validates load, node, and solar subentry migrations for their sectioned fields.
  redundancy: Covers three element types in one test; no other tests cover these paths.
  decision_rationale: Keep; could split later if element-specific coverage needs isolation.
---

# Behavior summary

Asserts migration mapping for load, node, and solar subentries, including forecasts, roles, and pricing/curtailment.

# Redundancy / overlap

No overlapping coverage elsewhere.

# Decision rationale

Keep. Consolidates migration behavior for simpler element types.

# Fixtures / setup

None.

# Next actions

Consider splitting into separate tests if failures need narrower diagnostics.
