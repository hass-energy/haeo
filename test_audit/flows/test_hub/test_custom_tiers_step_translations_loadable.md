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
  nodeid: tests/flows/test_hub.py::test_custom_tiers_step_translations_loadable
  source_file: tests/flows/test_hub.py
  test_class: ''
  test_function: test_custom_tiers_step_translations_loadable
  fixtures: []
  markers: []
notes:
  behavior: Custom tiers step translation keys load.
  redundancy: Translation coverage for custom tiers.
  decision_rationale: Keep. Ensures translations exist.
---

# Behavior summary

Custom tiers translation keys are present.

# Redundancy / overlap

Complementary to user step translations.

# Decision rationale

Keep. Prevents missing translations.

# Fixtures / setup

Uses async_get_translations.

# Next actions

None.
