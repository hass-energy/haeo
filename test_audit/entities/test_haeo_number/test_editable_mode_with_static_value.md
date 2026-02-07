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
  nodeid: tests/entities/test_haeo_number.py::test_editable_mode_with_static_value
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_editable_mode_with_static_value
  fixtures: []
  markers: []
notes:
  behavior: Editable mode initializes with static config value and attributes.
  redundancy: Core entity behavior.
  decision_rationale: Keep. Validates editable initialization and attributes.
---

# Behavior summary

Editable entity uses config value, sets units, range, and attributes.

# Redundancy / overlap

Foundational editable behavior.

# Decision rationale

Keep. Baseline entity initialization.

# Fixtures / setup

Uses subentry with constant value and power field info.

# Next actions

None.
