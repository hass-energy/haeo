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
  nodeid: tests/test_translations.py::test_all_output_names_have_translations
  source_file: tests/test_translations.py
  test_class: ''
  test_function: test_all_output_names_have_translations
  fixtures: []
  markers: []
notes:
  behavior: Ensures every output name has a translation entry under entity.sensor.
  redundancy: Complementary to unused translation test.
  decision_rationale: Keep. Validates coverage of output translations.
---

# Behavior summary

Checks that all output names in the model have corresponding sensor translations.

# Redundancy / overlap

No overlap with unused translation tests; this covers missing translations.

# Decision rationale

Keep. Translation coverage is critical.

# Fixtures / setup

Uses translation file parsing.

# Next actions

None.
