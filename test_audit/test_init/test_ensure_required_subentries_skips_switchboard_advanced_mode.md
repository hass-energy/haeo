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
  nodeid: tests/test_init.py::test_ensure_required_subentries_skips_switchboard_advanced_mode
  source_file: tests/test_init.py
  test_class: ''
  test_function: test_ensure_required_subentries_skips_switchboard_advanced_mode
  fixtures: []
  markers: []
notes:
  behavior: Does not create a switchboard node when advanced mode is enabled.
  redundancy: Distinct branch for advanced mode.
  decision_rationale: Keep. Validates advanced-mode behavior.
---

# Behavior summary

Asserts `_ensure_required_subentries` skips creating the default node when advanced mode is enabled.

# Redundancy / overlap

No overlap with non-advanced creation test.

# Decision rationale

Keep. Advanced mode should not auto-create nodes.

# Fixtures / setup

Uses a separate advanced-mode hub entry.

# Next actions

None.
