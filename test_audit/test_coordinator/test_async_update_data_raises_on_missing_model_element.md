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
  nodeid: tests/test_coordinator.py::test_async_update_data_raises_on_missing_model_element
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_update_data_raises_on_missing_model_element
  fixtures: []
  markers: []
notes:
  behavior: Raises when adapter output references a missing model element.
  redundancy: Distinct error path.
  decision_rationale: Keep. Validates adapter/model consistency handling.
---

# Behavior summary

Coordinator surfaces missing model element references during output build.

# Redundancy / overlap

No overlap with other error paths.

# Decision rationale

Keep. Ensures clear failure for inconsistent outputs.

# Fixtures / setup

Mocks adapter outputs with missing element.

# Next actions

None.
