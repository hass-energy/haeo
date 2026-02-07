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
  nodeid: tests/test_init.py::test_async_setup_entry_initializes_coordinator
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_async_setup_entry_initializes_coordinator
  fixtures: []
  markers: []
notes:
  behavior: Creates coordinator, initializes/refreshes, wires runtime data, and forwards platforms.
  redundancy: Foundational setup coverage; not duplicated elsewhere.
  decision_rationale: Keep. Core setup behavior.
---

# Behavior summary

Mocks coordinator creation and asserts initialization, refresh, runtime data wiring, and platform forwarding calls.

# Redundancy / overlap

No overlap with error-path setup tests.

# Decision rationale

Keep. This test validates the happy-path setup flow.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

None.
