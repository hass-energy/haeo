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
  nodeid: tests/entities/test_haeo_number.py::test_driven_mode_ignores_user_set_value
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_driven_mode_ignores_user_set_value
  fixtures: []
  markers: []
notes:
  behavior: Driven mode ignores user-set native values.
  redundancy: Distinct from editable set behavior.
  decision_rationale: Keep. Ensures driven mode is read-only.
---

# Behavior summary

`async_set_native_value()` does not change value in driven mode.

# Redundancy / overlap

Complements editable-mode set tests.

# Decision rationale

Keep. Protects driven behavior.

# Fixtures / setup

Mocks write state and preloaded value.

# Next actions

None.
