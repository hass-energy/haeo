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
  nodeid: tests/test_init.py::test_setup_preserves_config_entry_error_exception
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_setup_preserves_config_entry_error_exception
  fixtures: []
  markers: []
notes:
  behavior: Preserves ConfigEntryError translation key from coordinator.
  redundancy: Complement to preserved ConfigEntryNotReady case.
  decision_rationale: Keep. Ensures error keys are not overridden.
---

# Behavior summary

Mocks coordinator to raise ConfigEntryError with custom key and asserts the key is preserved.

# Redundancy / overlap

No overlap with wrapped error cases.

# Decision rationale

Keep. Preserving translation keys is required for correct error display.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

None.
