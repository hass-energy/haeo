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
  nodeid: tests/entities/test_haeo_number.py::test_handle_horizon_change_driven_triggers_reload
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_handle_horizon_change_driven_triggers_reload
  fixtures: []
  markers: []
notes:
  behavior: Driven horizon change triggers reload task.
  redundancy: No explicit assertions; covered by timestamp update test.
  decision_rationale: Combine with stronger driven horizon change test.
---

# Behavior summary

Triggers reload on horizon change in driven mode.

# Redundancy / overlap

Overlaps with driven horizon change timestamp test.

# Decision rationale

Combine. Prefer assertive test.

# Fixtures / setup

Mocks loader and adds entity to platform.

# Next actions

Consider merging into driven timestamp test.
