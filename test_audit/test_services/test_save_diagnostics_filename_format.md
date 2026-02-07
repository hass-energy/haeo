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
  nodeid: tests/test_services.py::test_save_diagnostics_filename_format
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_save_diagnostics_filename_format
  fixtures: []
  markers: []
notes:
  behavior: Validates diagnostics file naming format and location.
  redundancy: Overlaps with diagnostics success test; can be combined.
  decision_rationale: Combine with diagnostics success test if consolidating.
---

# Behavior summary

Ensures diagnostics filename matches expected timestamp format in the correct directory.

# Redundancy / overlap

Overlaps with diagnostics success test.

# Decision rationale

Combine. The format assertion can be added to the success test.

# Fixtures / setup

Uses Home Assistant fixtures, mock config entry, and temp directory.

# Next actions

Consider merging into `test_save_diagnostics_service_success`.
