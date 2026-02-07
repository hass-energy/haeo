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
  nodeid: tests/test_init.py::test_ensure_required_subentries_skips_switchboard_if_exists
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_ensure_required_subentries_skips_switchboard_if_exists
  fixtures: []
  markers: []
notes:
  behavior: Skips creating a switchboard node when a node already exists.
  redundancy: Related to non-advanced creation test; can be parametrized.
  decision_rationale: Combine with non-advanced creation as a parameterized case.
---

# Behavior summary

Creates a node subentry first, runs `_ensure_required_subentries`, and asserts no additional node is created.

# Redundancy / overlap

Overlaps with switchboard creation test; same function with different preconditions.

# Decision rationale

Combine. Parameterize on existing-node vs missing-node.

# Fixtures / setup

Uses `mock_hub_entry`.

# Next actions

Consider merging with `test_ensure_required_subentries_creates_switchboard_non_advanced`.
