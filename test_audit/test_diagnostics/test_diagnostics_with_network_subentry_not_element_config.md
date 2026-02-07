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
  nodeid: tests/test_diagnostics.py::test_diagnostics_with_network_subentry_not_element_config
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_diagnostics_with_network_subentry_not_element_config
  fixtures: []
  markers: []
notes:
  behavior: Includes invalid element config in participants but yields no inputs.
  redundancy: Distinct invalid-config path.
  decision_rationale: Keep. Ensures diagnostics tolerate invalid element configs.
---

# Behavior summary

Subentry with invalid element config is reported but does not produce inputs.

# Redundancy / overlap

No overlap with network-subentry skip test.

# Decision rationale

Keep. Invalid configs should not crash diagnostics.

# Fixtures / setup

Uses Home Assistant fixtures and mock subentries.

# Next actions

None.
