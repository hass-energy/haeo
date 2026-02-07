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
  nodeid: tests/flows/test_hub_flow.py::test_subentry_translations_exist
  source_file: tests/flows/test_hub_flow.py
  test_class: ''
  test_function: test_subentry_translations_exist
  fixtures: []
  markers: []
notes:
  behavior: Subentry translation keys exist for element types.
  redundancy: Translation coverage for subentries.
  decision_rationale: Keep. Ensures translation keys exist.
---

# Behavior summary

Subentry translation keys are present.

# Redundancy / overlap

Complementary to hub translations tests.

# Decision rationale

Keep. Prevents missing translations.

# Fixtures / setup

Uses async_get_translations and element registry.

# Next actions

None.
