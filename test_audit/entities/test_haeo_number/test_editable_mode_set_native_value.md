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
  nodeid: tests/entities/test_haeo_number.py::test_editable_mode_set_native_value
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_editable_mode_set_native_value
  fixtures: []
  markers: []
notes:
  behavior: Editable mode updates value, writes state, and persists config.
  redundancy: Core editable behavior.
  decision_rationale: Keep. Validates user updates are persisted.
---

# Behavior summary

`async_set_native_value()` updates value, writes state, and updates subentry.

# Redundancy / overlap

Distinct from driven mode behavior.

# Decision rationale

Keep. Ensures user updates persist.

# Fixtures / setup

Mocks write state and subentry update.

# Next actions

None.
