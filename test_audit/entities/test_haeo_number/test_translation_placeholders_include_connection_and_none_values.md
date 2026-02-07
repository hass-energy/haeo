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
  nodeid: tests/entities/test_haeo_number.py::test_translation_placeholders_include_connection_and_none_values
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_translation_placeholders_include_connection_and_none_values
  fixtures: []
  markers: []
notes:
  behavior: Translation placeholders include connection target and empty string for None values.
  redundancy: Covers None/connection handling.
  decision_rationale: Keep. Ensures placeholders handle special values.
---

# Behavior summary

Connection targets and None values are represented correctly in placeholders.

# Redundancy / overlap

Distinct from generic placeholder test.

# Decision rationale

Keep. Protects placeholder formatting.

# Fixtures / setup

Uses subentry with connection and None schema values.

# Next actions

None.
