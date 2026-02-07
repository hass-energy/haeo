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
  nodeid: tests/test_coordinator.py::test_coordinator_initialization_collects_participants
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_coordinator_initialization_collects_participants
  fixtures: []
  markers: []
notes:
  behavior: Builds participant map from element subentries during coordinator initialization.
  redundancy: Core initialization behavior; no overlap with other tests.
  decision_rationale: Keep. Verifies initialization wiring.
---

# Behavior summary

Builds the participant mapping from subentries as part of coordinator initialization.

# Redundancy / overlap

No overlap with other initialization tests.

# Decision rationale

Keep. Ensures participant mapping is correct.

# Fixtures / setup

Uses basic coordinator setup.

# Next actions

None.
