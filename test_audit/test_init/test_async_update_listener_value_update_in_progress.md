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
  nodeid: tests/test_init.py::test_async_update_listener_value_update_in_progress
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_async_update_listener_value_update_in_progress
  fixtures: []
  markers: []
notes:
  behavior: Clears value_update_in_progress, signals stale optimization, and skips reload.
  redundancy: Structure overlaps with no-coordinator variant; candidate for parametrization.
  decision_rationale: Combine with no-coordinator variant as a parametrized case.
---

# Behavior summary

With coordinator present, asserts the flag is cleared, stale optimization is signaled, and reload is skipped.

# Redundancy / overlap

Overlaps with the no-coordinator variant; same flag-clearing behavior.

# Decision rationale

Combine. Parametrize coordinator present vs None.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

Consider merging with `test_async_update_listener_value_update_skips_refresh_without_coordinator`.
