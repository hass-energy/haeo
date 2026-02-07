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
  nodeid: tests/entities/test_haeo_switch.py::test_async_added_to_hass_editable_uses_config_value
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_async_added_to_hass_editable_uses_config_value
  fixtures: []
  markers: []
notes:
  behavior: Editable mode uses config value on add.
  redundancy: Core lifecycle behavior.
  decision_rationale: Keep. Ensures initial state.
---

# Behavior summary

`async_added_to_hass()` uses config value in editable mode.

# Redundancy / overlap

Distinct from defaults/missing and driven add tests.

# Decision rationale

Keep. Validates lifecycle.

# Fixtures / setup

Adds entity to platform.

# Next actions

None.
