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
  nodeid: tests/test_init.py::test_async_setup_entry_returns_false_when_network_subentry_missing
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_async_setup_entry_returns_false_when_network_subentry_missing
  fixtures: []
  markers: []
notes:
  behavior: Returns False if required network subentry cannot be created.
  redundancy: Unique negative-path for subentry creation failure.
  decision_rationale: Keep. Validates required subentry enforcement.
---

# Behavior summary

Mocks `_ensure_required_subentries` to do nothing and asserts setup returns False.

# Redundancy / overlap

No overlap with network creation tests.

# Decision rationale

Keep. Ensures setup fails when required subentries are missing.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

None.
