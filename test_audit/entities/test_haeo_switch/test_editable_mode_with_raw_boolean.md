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
  nodeid: tests/entities/test_haeo_switch.py::test_editable_mode_with_raw_boolean
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_editable_mode_with_raw_boolean
  fixtures: []
  markers: []
notes:
  behavior: Editable mode accepts raw boolean config values.
  redundancy: Covers non-schema boolean input.
  decision_rationale: Keep. Ensures raw bool handling.
---

# Behavior summary

Raw boolean config values initialize switch correctly.

# Redundancy / overlap

Distinct from schema-wrapped constants.

# Decision rationale

Keep. Protects backward compatibility.

# Fixtures / setup

Uses subentry with raw boolean.

# Next actions

None.
