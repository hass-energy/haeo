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
  nodeid: tests/entities/test_haeo_switch.py::test_driven_mode_with_entity_id
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_driven_mode_with_entity_id
  fixtures: []
  markers: []
notes:
  behavior: Driven mode tracks a source entity ID.
  redundancy: Core driven configuration behavior.
  decision_rationale: Keep. Validates driven setup.
---

# Behavior summary

Driven switch stores source entity ID and mode.

# Redundancy / overlap

Distinct from driven load tests.

# Decision rationale

Keep. Ensures driven configuration.

# Fixtures / setup

Uses subentry with entity ID.

# Next actions

None.
