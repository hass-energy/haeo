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
  nodeid: tests/flows/test_hub.py::test_create_horizon_preset_raises_on_invalid_days
  source_file: tests/flows/test_hub.py
  test_class: ''
  test_function: test_create_horizon_preset_raises_on_invalid_days
  fixtures: []
  markers: []
notes:
  behavior: Invalid day count raises ValueError.
  redundancy: Input validation coverage.
  decision_rationale: Keep. Ensures preset validation.
---

# Behavior summary

\_create_horizon_preset rejects values below minimum days.

# Redundancy / overlap

Distinct from schema tests.

# Decision rationale

Keep. Prevents invalid presets.

# Fixtures / setup

Uses flows module helper.

# Next actions

None.
