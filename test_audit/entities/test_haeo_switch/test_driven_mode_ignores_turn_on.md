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
  nodeid: tests/entities/test_haeo_switch.py::test_driven_mode_ignores_turn_on
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_driven_mode_ignores_turn_on
  fixtures: []
  markers: []
notes:
  behavior: Driven mode ignores turn_on actions.
  redundancy: Pairs with turn_off ignore test.
  decision_rationale: Keep. Ensures driven switch is read-only.
---

# Behavior summary

`async_turn_on()` does not change driven state.

# Redundancy / overlap

Complementary to turn_off ignore test.

# Decision rationale

Keep. Protects driven read-only behavior.

# Fixtures / setup

Preloads driven state and mocks writes.

# Next actions

None.
