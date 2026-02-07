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
  nodeid: tests/test_translations.py::test_no_unused_device_translations
  source_file: tests/test_translations.py
  test_class: ''
  test_function: test_no_unused_device_translations
  fixtures: []
  markers: []
notes:
  behavior: Ensures device translation keys are used by known devices (allowing network).
  redundancy: Complementary to missing device translation test.
  decision_rationale: Keep. Prevents stale device translations.
---

# Behavior summary

Checks that all device translation keys map to known devices.

# Redundancy / overlap

No overlap with missing device translation test.

# Decision rationale

Keep. Prevents unused device translation keys.

# Fixtures / setup

Uses translation file parsing.

# Next actions

None.
