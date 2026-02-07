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
  nodeid: tests/flows/test_hub.py::test_user_step_form_has_translations
  source_file: tests/flows/test_hub.py
  test_class: ''
  test_function: test_user_step_form_has_translations
  fixtures: []
  markers: []
notes:
  behavior: User step form fields have translation keys.
  redundancy: Ensures field-level translation coverage.
  decision_rationale: Keep. Prevents untranslated fields.
---

# Behavior summary

All user step form sections and fields map to translation keys.

# Redundancy / overlap

More granular than translation-loadable tests.

# Decision rationale

Keep. Validates UI translation coverage.

# Fixtures / setup

Uses HubConfigFlow form schema.

# Next actions

None.
