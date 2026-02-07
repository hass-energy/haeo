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
  nodeid: tests/flows/test_hub.py::test_config_error_translations_exist
  source_file: tests/flows/test_hub.py
  test_class: ''
  test_function: test_config_error_translations_exist
  fixtures: []
  markers: []
notes:
  behavior: Error translation keys exist for hub config flow.
  redundancy: Translation coverage for errors.
  decision_rationale: Keep. Ensures error messages localized.
---

# Behavior summary

Hub config error translations are present.

# Redundancy / overlap

Complementary to abort translations test.

# Decision rationale

Keep. Prevents missing error translations.

# Fixtures / setup

Uses async_get_translations.

# Next actions

None.
