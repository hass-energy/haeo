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
  nodeid: tests/test_coordinator.py::test_subscribe_to_input_entities_no_op_without_runtime_data
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_subscribe_to_input_entities_no_op_without_runtime_data
  fixtures: []
  markers: []
notes:
  behavior: Skips subscriptions when runtime data is missing.
  redundancy: Unique no-op branch.
  decision_rationale: Keep. Avoids errors when runtime data is absent.
---

# Behavior summary

No subscriptions are created if runtime data is missing.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Validates defensive behavior.

# Fixtures / setup

Mocks missing runtime data.

# Next actions

None.
