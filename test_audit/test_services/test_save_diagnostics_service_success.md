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
  nodeid: tests/test_services.py::test_save_diagnostics_service_success
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_save_diagnostics_service_success
  fixtures: []
  markers: []
notes:
  behavior: Writes diagnostics file and includes expected wrapper keys and payload.
  redundancy: Overlaps with filename format test on file creation but adds full payload validation.
  decision_rationale: Keep. Validates full diagnostics output structure.
---

# Behavior summary

Runs save_diagnostics service, writes file, and validates wrapper and data content.

# Redundancy / overlap

Partial overlap with filename format test.

# Decision rationale

Keep. Ensures correct diagnostics payload.

# Fixtures / setup

Uses Home Assistant fixtures, mock config entry, and temp directory.

# Next actions

None.
