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
  nodeid: tests/entities/test_haeo_number.py::test_driven_mode_with_v01_single_entity_string
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_driven_mode_with_v01_single_entity_string
  fixtures: []
  markers: []
notes:
  behavior: Driven mode handles legacy single-entity string format.
  redundancy: Back-compat coverage.
  decision_rationale: Keep. Protects upgrade compatibility.
---

# Behavior summary

Legacy string entity IDs are normalized into a list.

# Redundancy / overlap

Distinct from list-based driven tests.

# Decision rationale

Keep. Ensures backward compatibility.

# Fixtures / setup

Uses v0.1 schema format.

# Next actions

None.
