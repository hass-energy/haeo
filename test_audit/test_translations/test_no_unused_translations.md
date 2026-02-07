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
  nodeid: tests/test_translations.py::test_no_unused_translations
  source_file: tests/test_translations.py
  test_class: ''
  test_function: test_no_unused_translations
  fixtures: []
  markers: []
notes:
  behavior: Ensures entity.sensor translation keys are used by outputs (allowing horizon).
  redundancy: Complementary to missing translation test.
  decision_rationale: Keep. Prevents stale sensor translations.
---

# Behavior summary

Checks that all sensor translation keys correspond to known output names.

# Redundancy / overlap

No overlap with missing translations; this covers unused keys.

# Decision rationale

Keep. Prevents unused translation keys.

# Fixtures / setup

Uses translation file parsing.

# Next actions

None.
