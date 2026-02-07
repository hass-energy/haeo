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
  nodeid: tests/test_system_health.py::test_async_register_callback
  source_file: tests/test_system_health.py
  test_class: ''
  test_function: test_async_register_callback
  fixtures: []
  markers: []
notes:
  behavior: Registers the system health callback with Home Assistant.
  redundancy: Unique registration behavior.
  decision_rationale: Keep. Verifies system health registration wiring.
---

# Behavior summary

Asserts `async_register` registers `async_system_health_info` with the system health registry.

# Redundancy / overlap

No overlap with system health output tests.

# Decision rationale

Keep. Registration is required for system health integration.

# Fixtures / setup

Uses `hass`.

# Next actions

None.
