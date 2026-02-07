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
  nodeid: tests/test_init.py::test_async_setup_entry_raises_config_entry_error_on_permanent_failure
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_async_setup_entry_raises_config_entry_error_on_permanent_failure
  fixtures: []
  markers: []
notes:
  behavior: Wraps permanent coordinator errors in ConfigEntryError with setup_failed_permanent key.
  redundancy: Complement to transient failure test.
  decision_rationale: Keep. Validates permanent failure mapping.
---

# Behavior summary

Mocks coordinator initialize to raise ValueError and asserts ConfigEntryError with setup_failed_permanent.

# Redundancy / overlap

No overlap with transient or preserved exception tests.

# Decision rationale

Keep. Ensures permanent failures are handled correctly.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

None.
