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
  nodeid: tests/test_translations.py::test_all_device_names_have_translations
  source_file: tests/test_translations.py
  test_class: ''
  test_function: test_all_device_names_have_translations
  fixtures: []
  markers: []
notes:
  behavior: Ensures every device name has a translation entry.
  redundancy: Complementary to unused device translation test.
  decision_rationale: Keep. Validates device translation coverage.
---

# Behavior summary

Checks that all device names have translations under the device section.

# Redundancy / overlap

No overlap with unused device translation test.

# Decision rationale

Keep. Device translation coverage is required.

# Fixtures / setup

Uses translation file parsing.

# Next actions

None.
