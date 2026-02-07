---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_switch.py::test_setup_with_entity_id_creates_driven_mode_entity
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_setup_with_entity_id_creates_driven_mode_entity
  fixtures: []
  markers: []
notes:
  behavior: Configuring curtailment via entity_id produces a driven-mode switch entity.
  redundancy: Related to curtailment boolean test; same creation path with different value type.
  decision_rationale: Combine with curtailment creation test into a parameterized value-type case.
---

# Behavior summary

Ensures entity_id configuration produces a driven-mode switch entity.

# Redundancy / overlap

Overlaps with curtailment boolean switch creation test.

# Decision rationale

Combine. Parameterize boolean vs entity_id inputs.

# Fixtures / setup

Uses Home Assistant fixtures and mock solar subentry.

# Next actions

Consider merging with `test_setup_creates_switch_entities_for_solar_curtailment`.
