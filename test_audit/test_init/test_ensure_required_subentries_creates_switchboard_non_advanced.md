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
  nodeid: tests/test_init.py::test_ensure_required_subentries_creates_switchboard_non_advanced
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_ensure_required_subentries_creates_switchboard_non_advanced
  fixtures: []
  markers: []
notes:
  behavior: Creates a default switchboard node when advanced mode is disabled.
  redundancy: Distinct from advanced-mode skip and existing-node cases.
  decision_rationale: Keep. Validates default node creation behavior.
---

# Behavior summary

Ensures `_ensure_required_subentries` creates the default switchboard node with expected defaults in non-advanced mode.

# Redundancy / overlap

No overlap with advanced-mode or existing-node tests.

# Decision rationale

Keep. Ensures default node setup for non-advanced mode.

# Fixtures / setup

Uses `mock_hub_entry`.

# Next actions

None.
