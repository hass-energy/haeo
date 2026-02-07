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
  nodeid: tests/test_services.py::test_async_setup_registers_service
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_async_setup_registers_service
  fixtures: []
  markers: []
notes:
  behavior: Registers the save_diagnostics service during async_setup.
  redundancy: Overlaps with optimize service registration test.
  decision_rationale: Combine with optimize registration test via parametrization.
---

# Behavior summary

Ensures async_setup registers the save_diagnostics service.

# Redundancy / overlap

Overlaps with optimize service registration test.

# Decision rationale

Combine. Parameterize expected service names.

# Fixtures / setup

Uses Home Assistant fixtures.

# Next actions

Consider merging with `test_async_setup_registers_optimize_service`.
