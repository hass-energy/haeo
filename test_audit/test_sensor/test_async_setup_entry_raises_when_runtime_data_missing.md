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
  nodeid: tests/test_sensor.py::test_async_setup_entry_raises_when_runtime_data_missing
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_async_setup_entry_raises_when_runtime_data_missing
  fixtures: []
  markers: []
notes:
  behavior: Raises ConfigEntryError when runtime data is missing during sensor setup.
  redundancy: Unique negative-path coverage.
  decision_rationale: Keep. Ensures required runtime data is enforced.
---

# Behavior summary

Asserts setup fails when runtime data is missing.

# Redundancy / overlap

No overlap with other setup tests.

# Decision rationale

Keep. Guards setup preconditions.

# Fixtures / setup

Uses Home Assistant fixtures and a mock config entry.

# Next actions

None.
