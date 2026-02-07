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
  nodeid: tests/test_data_loading.py::test_create_network_add_failure_is_wrapped
  source_file: tests/test_data_loading.py
  test_class: ''
  test_function: test_create_network_add_failure_is_wrapped
  fixtures: []
  markers: []
notes:
  behavior: Wraps Network.add failures in a ValueError with a targeted message.
  redundancy: Unique error-wrapping coverage.
  decision_rationale: Keep. Ensures errors are surfaced with context.
---

# Behavior summary

Asserts create_network wraps Network.add errors with a descriptive ValueError.

# Redundancy / overlap

No overlap with success-path tests.

# Decision rationale

Keep. Error handling is critical.

# Fixtures / setup

Uses Home Assistant fixtures and mock participants.

# Next actions

None.
