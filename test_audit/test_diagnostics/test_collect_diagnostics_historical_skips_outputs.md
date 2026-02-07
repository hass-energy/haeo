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
  nodeid: tests/test_diagnostics.py::test_collect_diagnostics_historical_skips_outputs
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_collect_diagnostics_historical_skips_outputs
  fixtures: []
  markers: []
notes:
  behavior: Historical diagnostics mark historical mode and omit outputs.
  redundancy: Overlaps with historical provider omits outputs test.
  decision_rationale: Combine with historical provider outputs test.
---

# Behavior summary

Asserts historical diagnostics omit outputs and set historical metadata.

# Redundancy / overlap

Duplicates the historical provider outputs test.

# Decision rationale

Combine. One historical-mode test is sufficient.

# Fixtures / setup

Uses Home Assistant fixtures and historical provider.

# Next actions

Consider merging with `test_diagnostics_with_historical_provider_omits_outputs`.
