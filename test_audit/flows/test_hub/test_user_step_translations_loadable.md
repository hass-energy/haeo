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
  nodeid: tests/flows/test_hub.py::test_user_step_translations_loadable
  source_file: tests/flows/test_hub.py
  test_class: ''
  test_function: test_user_step_translations_loadable
  fixtures: []
  markers: []
notes:
  behavior: User step translation keys load for hub flow.
  redundancy: Translation coverage for hub flow.
  decision_rationale: Keep. Ensures translations exist.
---

# Behavior summary

Hub user step translation keys are present.

# Redundancy / overlap

Complementary to other translation tests.

# Decision rationale

Keep. Prevents missing translations.

# Fixtures / setup

Uses async_get_translations.

# Next actions

None.
