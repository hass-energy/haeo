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
  nodeid: tests/entities/test_haeo_number.py::test_translation_placeholders_from_subentry_data
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_translation_placeholders_from_subentry_data
  fixtures: []
  markers: []
notes:
  behavior: Translation placeholders come from subentry fields, including extra keys.
  redundancy: Specific to placeholder generation.
  decision_rationale: Keep. Ensures translation data is populated.
---

# Behavior summary

Subentry values are exposed as translation placeholders.

# Redundancy / overlap

Distinct from connection/None placeholder test.

# Decision rationale

Keep. Protects placeholder generation.

# Fixtures / setup

Uses subentry data with extra key.

# Next actions

None.
