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
  nodeid: tests/test_init.py::test_ensure_required_subentries_network_already_exists
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_ensure_required_subentries_network_already_exists
  fixtures: []
  markers: []
notes:
  behavior: Ensures network subentry is not duplicated if already present.
  redundancy: Complements network creation test.
  decision_rationale: Keep. Validates idempotent subentry creation.
---

# Behavior summary

Creates a network subentry, runs `_ensure_required_subentries`, and asserts only one remains.

# Redundancy / overlap

No overlap with network creation test; this covers the skip path.

# Decision rationale

Keep. Ensures idempotency for required subentries.

# Fixtures / setup

Uses `mock_hub_entry`.

# Next actions

None.
