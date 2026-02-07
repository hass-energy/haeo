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
  nodeid: tests/migrations/test_v1_3.py::test_async_migrate_entry_updates_entry_and_subentries
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_async_migrate_entry_updates_entry_and_subentries
  fixtures: []
  markers: []
notes:
  behavior: Runs async migration end-to-end, asserting entry version/data updates and subentry migration.
  redundancy: Only end-to-end migration test with subentry updates.
  decision_rationale: Keep to validate the main async migration path.
---

# Behavior summary

Creates a hub entry with subentry, runs async migration, and asserts version, data sections, options, and migrated subentry data.

# Redundancy / overlap

Unique end-to-end migration test for v1.3.

# Decision rationale

Keep. It validates the high-level migration flow.

# Fixtures / setup

Uses Home Assistant fixture for config entries.

# Next actions

None.
