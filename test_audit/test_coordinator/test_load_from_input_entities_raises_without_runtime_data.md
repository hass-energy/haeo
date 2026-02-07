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
  nodeid: tests/test_coordinator.py::test_load_from_input_entities_raises_without_runtime_data
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_load_from_input_entities_raises_without_runtime_data
  fixtures: []
  markers: []
notes:
  behavior: Raises UpdateFailed when runtime data is missing during input load.
  redundancy: Related to async initialization missing runtime data.
  decision_rationale: Keep. Guard clause for input loading.
---

# Behavior summary

Input loading fails when runtime data is absent.

# Redundancy / overlap

Distinct guard from async initialization check.

# Decision rationale

Keep. Ensures clear error when runtime data missing.

# Fixtures / setup

Mocks missing runtime data.

# Next actions

None.
