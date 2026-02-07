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
  nodeid: tests/coordinator/test_network.py::test_update_element_raises_for_missing_model_element
  source_file: tests/coordinator/test_network.py
  test_class: ''
  test_function: test_update_element_raises_for_missing_model_element
  fixtures: []
  markers: []
notes:
  behavior: Ensures update_element raises when the target model element does not exist in the network.
  redundancy: No other test asserts this specific error path for update_element.
  decision_rationale: Protects the explicit failure mode required by coordinator updates.
---

# Behavior summary

Creates a network without the target connection and asserts update_element raises the expected ValueError message.

# Redundancy / overlap

Unique coverage for missing-element error handling in update_element.

# Decision rationale

Keep. It validates the failure path for invalid update requests.

# Fixtures / setup

None.

# Next actions

None.
