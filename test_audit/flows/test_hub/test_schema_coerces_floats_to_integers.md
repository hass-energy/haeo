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
  nodeid: tests/flows/test_hub.py::test_schema_coerces_floats_to_integers
  source_file: tests/flows/test_hub.py
  test_class: ''
  test_function: test_schema_coerces_floats_to_integers
  fixtures: []
  markers: []
notes:
  behavior: Custom tiers schema coerces float inputs to integers.
  redundancy: Validation behavior for tier inputs.
  decision_rationale: Keep. Ensures coercion works.
---

# Behavior summary

Float tier counts/durations are coerced to ints.

# Redundancy / overlap

Distinct from field presence tests.

# Decision rationale

Keep. Prevents validation regressions.

# Fixtures / setup

Uses custom tiers schema validation.

# Next actions

None.
