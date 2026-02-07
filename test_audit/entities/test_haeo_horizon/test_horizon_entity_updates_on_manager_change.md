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
  nodeid: tests/entities/test_haeo_horizon.py::test_horizon_entity_updates_on_manager_change
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_horizon_entity_updates_on_manager_change
  fixtures: []
  markers: []
notes:
  behavior: Manager change triggers state write.
  redundancy: Core update behavior.
  decision_rationale: Keep. Ensures update handling writes state.
---

# Behavior summary

Horizon change handler writes state.

# Redundancy / overlap

Distinct from timestamp alignment tests.

# Decision rationale

Keep. Prevents update regressions.

# Fixtures / setup

Mocks async_write_ha_state.

# Next actions

None.
