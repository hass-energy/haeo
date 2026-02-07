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
  nodeid: tests/test_init.py::test_ensure_required_subentries_creates_network
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_ensure_required_subentries_creates_network
  fixtures: []
  markers: []
notes:
  behavior: Creates the network subentry when it is missing.
  redundancy: Complements network already-exists test.
  decision_rationale: Keep. Validates required subentry creation.
---

# Behavior summary

Runs `_ensure_required_subentries` on a hub entry with no network subentry and asserts creation.

# Redundancy / overlap

No overlap with skip-path test; this covers the creation path.

# Decision rationale

Keep. Ensures required subentries are added.

# Fixtures / setup

Uses `mock_hub_entry`.

# Next actions

None.
