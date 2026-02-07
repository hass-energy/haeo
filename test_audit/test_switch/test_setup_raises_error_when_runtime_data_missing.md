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
  nodeid: tests/test_switch.py::test_setup_raises_error_when_runtime_data_missing
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_setup_raises_error_when_runtime_data_missing
  fixtures: []
  markers: []
notes:
  behavior: Raises ConfigEntryError when runtime data is missing during switch setup.
  redundancy: Unique negative path for missing runtime data.
  decision_rationale: Keep. Validates error handling for invalid setup state.
---

# Behavior summary

Ensures setup raises when the config entry lacks runtime data.

# Redundancy / overlap

No overlap with switch creation tests.

# Decision rationale

Keep. Guards a required precondition for setup.

# Fixtures / setup

Uses Home Assistant fixtures and a mock config entry.

# Next actions

None.
