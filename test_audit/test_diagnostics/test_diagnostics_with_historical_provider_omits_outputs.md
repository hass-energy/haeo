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
  nodeid: tests/test_diagnostics.py::test_diagnostics_with_historical_provider_omits_outputs
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_diagnostics_with_historical_provider_omits_outputs
  fixtures: []
  markers: []
notes:
  behavior: Historical diagnostics omit outputs and set historical flag.
  redundancy: Duplicates historical skips outputs test.
  decision_rationale: Combine with `test_collect_diagnostics_historical_skips_outputs`.
---

# Behavior summary

Ensures historical diagnostics omit outputs and set environment flags appropriately.

# Redundancy / overlap

Overlaps with `test_collect_diagnostics_historical_skips_outputs`.

# Decision rationale

Combine. Single historical-mode test is sufficient.

# Fixtures / setup

Uses Home Assistant fixtures and historical provider.

# Next actions

Consider merging with `test_collect_diagnostics_historical_skips_outputs`.
