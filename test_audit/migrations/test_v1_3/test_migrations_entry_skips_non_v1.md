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
  nodeid: tests/migrations/test_v1_3.py::test_migrations_entry_skips_non_v1
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_migrations_entry_skips_non_v1
  fixtures: []
  markers: []
notes:
  behavior: Ensures migration dispatcher skips handlers for non-v1 entries.
  redundancy: Unique coverage for version gating in dispatcher.
  decision_rationale: Keep to prevent unintended migration dispatch.
---

# Behavior summary

Sets entry version to 2 and asserts migration handlers are not invoked.

# Redundancy / overlap

No overlap; only test for non-v1 skip logic.

# Decision rationale

Keep. Protects dispatcher version filtering.

# Fixtures / setup

Uses Home Assistant fixture and monkeypatch.

# Next actions

None.
