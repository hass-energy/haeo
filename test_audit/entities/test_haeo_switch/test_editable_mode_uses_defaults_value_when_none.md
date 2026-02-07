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
  nodeid: tests/entities/test_haeo_switch.py::test_editable_mode_uses_defaults_value_when_none
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_editable_mode_uses_defaults_value_when_none
  fixtures: []
  markers: []
notes:
  behavior: Editable mode uses defaults.value after add when config is None.
  redundancy: Specific to defaults handling.
  decision_rationale: Keep. Ensures defaults applied.
---

# Behavior summary

Defaults are applied on add when config value is None.

# Redundancy / overlap

Complementary to missing-value defaults test.

# Decision rationale

Keep. Validates defaults behavior.

# Fixtures / setup

Uses field info defaults and None config value.

# Next actions

None.
