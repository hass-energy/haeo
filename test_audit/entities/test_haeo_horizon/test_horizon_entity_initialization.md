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
  nodeid: tests/entities/test_haeo_horizon.py::test_horizon_entity_initialization
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_horizon_entity_initialization
  fixtures: []
  markers: []
notes:
  behavior: Horizon entity initializes with unique ID, translation key, and no polling.
  redundancy: Core initialization behavior.
  decision_rationale: Keep. Validates baseline entity setup.
---

# Behavior summary

Entity initialization sets ID, translation key, and polling behavior.

# Redundancy / overlap

Foundational init test.

# Decision rationale

Keep. Prevents init regressions.

# Fixtures / setup

Uses config entry and horizon manager.

# Next actions

None.
