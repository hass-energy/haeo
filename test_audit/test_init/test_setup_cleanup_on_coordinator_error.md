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
  nodeid: tests/test_init.py::test_setup_cleanup_on_coordinator_error
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_setup_cleanup_on_coordinator_error
  fixtures: []
  markers: []
notes:
  behavior: Wraps coordinator initialization runtime error in ConfigEntryNotReady with transient key.
  redundancy: Distinct from permanent failure and preserved exception tests.
  decision_rationale: Keep. Validates transient failure wrapping.
---

# Behavior summary

Mocks coordinator initialize to raise RuntimeError and asserts ConfigEntryNotReady with setup_failed_transient.

# Redundancy / overlap

No overlap with permanent failure or preserved exception cases.

# Decision rationale

Keep. Ensures transient errors are wrapped correctly.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

None.
