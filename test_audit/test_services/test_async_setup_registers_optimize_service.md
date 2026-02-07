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
  nodeid: tests/test_services.py::test_async_setup_registers_optimize_service
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_async_setup_registers_optimize_service
  fixtures: []
  markers: []
notes:
  behavior: Registers the optimize service during async_setup.
  redundancy: Overlaps with save_diagnostics registration test.
  decision_rationale: Combine with save_diagnostics registration test via parametrization.
---

# Behavior summary

Ensures async_setup registers the optimize service.

# Redundancy / overlap

Overlaps with save_diagnostics registration test.

# Decision rationale

Combine. Parameterize expected service names.

# Fixtures / setup

Uses Home Assistant fixtures.

# Next actions

Consider merging with `test_async_setup_registers_service`.
