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
  nodeid: tests/coordinator/test_network.py::test_update_element_updates_tracked_params
  source_file: tests/coordinator/test_network.py
  test_class: ''
  test_function: test_update_element_updates_tracked_params
  fixtures: []
  markers: []
notes:
  behavior: Verifies update_element updates tracked segment parameters on an existing connection element.
  redundancy: No overlap detected; this is the only test asserting tracked segment updates after config changes.
  decision_rationale: Covers critical behavior for updating connection power limits via coordinator updates.
---

# Behavior summary

Builds a minimal network, confirms initial connection segment limits, runs update_element, and asserts the tracked segment values are updated.

# Redundancy / overlap

Unique coverage of in-place TrackedParam updates on an existing model element.

# Decision rationale

Keep. This test validates coordinator update behavior and guards against regressions in tracked parameter refresh.

# Fixtures / setup

None.

# Next actions

None.
