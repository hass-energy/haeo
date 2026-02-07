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
  nodeid: tests/entities/test_haeo_switch.py::test_async_added_to_hass_driven_subscribes_to_source
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_async_added_to_hass_driven_subscribes_to_source
  fixtures: []
  markers: []
notes:
  behavior: Driven mode loads state from source on add.
  redundancy: Core driven lifecycle behavior.
  decision_rationale: Keep. Ensures source subscription loads state.
---

# Behavior summary

`async_added_to_hass()` loads driven state from source entity.

# Redundancy / overlap

Distinct from editable add tests.

# Decision rationale

Keep. Validates driven lifecycle.

# Fixtures / setup

Sets source state before add.

# Next actions

None.
