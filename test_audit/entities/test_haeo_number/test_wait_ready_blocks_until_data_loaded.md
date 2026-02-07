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
  nodeid: tests/entities/test_haeo_number.py::test_wait_ready_blocks_until_data_loaded
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_wait_ready_blocks_until_data_loaded
  fixtures: []
  markers: []
notes:
  behavior: wait_ready blocks until data loaded event is set.
  redundancy: Companion to is_ready test.
  decision_rationale: Keep. Ensures readiness waiting semantics.
---

# Behavior summary

`wait_ready()` waits until forecast update marks ready.

# Redundancy / overlap

Complementary to readiness flag test.

# Decision rationale

Keep. Validates async wait behavior.

# Fixtures / setup

Uses asyncio task and forecast update.

# Next actions

None.
