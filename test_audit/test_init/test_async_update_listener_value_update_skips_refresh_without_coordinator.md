---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_init.py::test_async_update_listener_value_update_skips_refresh_without_coordinator
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_async_update_listener_value_update_skips_refresh_without_coordinator
  fixtures: []
  markers: []
notes:
  behavior: Clears value_update_in_progress and skips reload when coordinator is None.
  redundancy: Structure overlaps with coordinator-present variant; candidate for parametrization.
  decision_rationale: Combine with coordinator-present variant as a parametrized case.
---

# Behavior summary

With no coordinator, asserts the flag is cleared and reload is skipped.

# Redundancy / overlap

Overlaps with coordinator-present case; shared behavior.

# Decision rationale

Combine. Parametrize coordinator presence.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

Consider merging with `test_async_update_listener_value_update_in_progress`.
