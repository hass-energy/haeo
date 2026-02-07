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
  nodeid: tests/entities/test_haeo_horizon.py::test_async_added_to_hass_subscribes_to_manager
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_async_added_to_hass_subscribes_to_manager
  fixtures: []
  markers: []
notes:
  behavior: Adding entity to hass subscribes to horizon manager and sets attributes.
  redundancy: Core lifecycle behavior.
  decision_rationale: Keep. Ensures subscription wiring.
---

# Behavior summary

`async_added_to_hass()` wires manager subscription and attributes.

# Redundancy / overlap

Distinct from update handler test.

# Decision rationale

Keep. Validates lifecycle wiring.

# Fixtures / setup

Adds entity to platform.

# Next actions

None.
