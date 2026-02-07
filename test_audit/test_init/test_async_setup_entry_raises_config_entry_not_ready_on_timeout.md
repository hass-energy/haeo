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
  nodeid: tests/test_init.py::test_async_setup_entry_raises_config_entry_not_ready_on_timeout
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_async_setup_entry_raises_config_entry_not_ready_on_timeout
  fixtures: []
  markers: []
notes:
  behavior: Raises ConfigEntryNotReady when input entities never become ready; checks translation key.
  redundancy: Distinct timeout failure path.
  decision_rationale: Keep. Validates readiness timeout handling.
---

# Behavior summary

Simulates never-ready input entities, asserts ConfigEntryNotReady is raised with the expected translation key.

# Redundancy / overlap

No overlap with coordinator failure or permanent error cases.

# Decision rationale

Keep. Ensures setup handles input readiness timeouts.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

None.
