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
  nodeid: tests/test_init.py::test_setup_preserves_config_entry_not_ready_exception
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_setup_preserves_config_entry_not_ready_exception
  fixtures: []
  markers: []
notes:
  behavior: Preserves ConfigEntryNotReady translation key from coordinator.
  redundancy: Complement to preserved ConfigEntryError case.
  decision_rationale: Keep. Ensures coordinator-provided keys are not overwritten.
---

# Behavior summary

Mocks coordinator to raise ConfigEntryNotReady with custom key and asserts the key is preserved.

# Redundancy / overlap

No overlap with wrapped error cases.

# Decision rationale

Keep. Preserving translation keys is important for error display.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

None.
