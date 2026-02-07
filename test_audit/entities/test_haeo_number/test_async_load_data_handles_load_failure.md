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
  nodeid: tests/entities/test_haeo_number.py::test_async_load_data_handles_load_failure
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_async_load_data_handles_load_failure
  fixtures: []
  markers: []
notes:
  behavior: Load failures do not raise and leave value unset.
  redundancy: Core error handling path.
  decision_rationale: Keep. Ensures failure handling is safe.
---

# Behavior summary

Loader exceptions are handled without updating state.

# Redundancy / overlap

Distinct from empty-value handling.

# Decision rationale

Keep. Prevents regressions in error handling.

# Fixtures / setup

Mocks loader to raise exception.

# Next actions

None.
