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
  nodeid: tests/test_diagnostics.py::test_diagnostics_with_outputs
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_diagnostics_with_outputs
  fixtures: []
  markers: []
notes:
  behavior: Includes output sensor states when coordinator exists, validating output path.
  redundancy: Unique output diagnostics coverage.
  decision_rationale: Keep. Output diagnostics are core functionality.
---

# Behavior summary

Ensures diagnostics include outputs when coordinator data is present.

# Redundancy / overlap

No overlap with participant-only diagnostics.

# Decision rationale

Keep. Output diagnostics must be captured.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator data.

# Next actions

None.
