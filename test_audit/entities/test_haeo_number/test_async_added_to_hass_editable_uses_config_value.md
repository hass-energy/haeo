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
  nodeid: tests/entities/test_haeo_number.py::test_async_added_to_hass_editable_uses_config_value
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_async_added_to_hass_editable_uses_config_value
  fixtures: []
  markers: []
notes:
  behavior: Editable mode uses config value on add without restore.
  redundancy: Core lifecycle behavior.
  decision_rationale: Keep. Ensures correct initial state.
---

# Behavior summary

`async_added_to_hass()` sets native value from config in editable mode.

# Redundancy / overlap

Distinct from driven-mode add behavior.

# Decision rationale

Keep. Validates add lifecycle.

# Fixtures / setup

Adds entity to platform.

# Next actions

None.
