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
  nodeid: tests/test_init.py::test_async_update_listener
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_async_update_listener
  fixtures: []
  markers: []
notes:
  behavior: Ensures update listener triggers reload and required subentry checks.
  redundancy: Distinct from value-update skip cases.
  decision_rationale: Keep. Validates normal update listener behavior.
---

# Behavior summary

Mocks reload and `_ensure_required_subentries`, then asserts both are invoked by `async_update_listener`.

# Redundancy / overlap

No overlap with value-update-in-progress variants.

# Decision rationale

Keep. Standard update listener path.

# Fixtures / setup

Uses `mock_hub_entry` and `monkeypatch`.

# Next actions

None.
