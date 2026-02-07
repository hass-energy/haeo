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
  nodeid: tests/test_coordinator.py::test_are_inputs_aligned_returns_false_without_runtime_data
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_are_inputs_aligned_returns_false_without_runtime_data
  fixtures: []
  markers: []
notes:
  behavior: Returns false when runtime data is missing.
  redundancy: Part of alignment guard cases.
  decision_rationale: Keep. Alignment depends on runtime data.
---

# Behavior summary

Alignment returns false when runtime data is unavailable.

# Redundancy / overlap

One of several alignment guard cases.

# Decision rationale

Keep. Ensures guard behavior.

# Fixtures / setup

Mocks missing runtime data.

# Next actions

None.
