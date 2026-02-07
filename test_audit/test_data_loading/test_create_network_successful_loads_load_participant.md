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
  nodeid: tests/test_data_loading.py::test_create_network_successful_loads_load_participant
  source_file: tests/test_data_loading.py
  test_class: ''
  test_function: test_create_network_successful_loads_load_participant
  fixtures: []
  markers: []
notes:
  behavior: Builds a network from loaded participant data, including period conversion and load element creation.
  redundancy: Unique coverage for loaded forecasts and period conversion.
  decision_rationale: Keep. Validates primary data loading behavior.
---

# Behavior summary

Ensures create_network builds a network with correct periods and includes the load participant.

# Redundancy / overlap

No overlap with empty-network or ordering tests.

# Decision rationale

Keep. Core network creation logic.

# Fixtures / setup

Uses Home Assistant fixtures and mock participants.

# Next actions

None.
