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
  nodeid: tests/test_coordinator.py::test_async_update_data_raises_when_runtime_data_none_in_body
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_update_data_raises_when_runtime_data_none_in_body
  fixtures: []
  markers: []
notes:
  behavior: Raises UpdateFailed if runtime data becomes None during update.
  redundancy: Distinct guard within update flow.
  decision_rationale: Keep. Protects update from invalid state.
---

# Behavior summary

Update fails if runtime data is missing inside the update body.

# Redundancy / overlap

Distinct from load-from-inputs missing data guard.

# Decision rationale

Keep. Ensures proper error on invalid runtime state.

# Fixtures / setup

Mocks runtime data removal.

# Next actions

None.
