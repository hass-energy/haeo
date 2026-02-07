---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_network_validation.py::test_validate_network_topology_with_battery_all_sections
  source_file: tests/test_network_validation.py
  test_class: ''
  test_function: test_validate_network_topology_with_battery_all_sections
  fixtures: []
  markers: []
notes:
  behavior: Battery with undercharge/overcharge sections still participates in connectivity.
  redundancy: Overlaps with minimal battery test; difference is optional section coverage.
  decision_rationale: Combine with minimal battery test if reducing duplication.
---

# Behavior summary

Asserts a battery with partition sections yields a connected topology including battery and main node.

# Redundancy / overlap

High overlap with `test_validate_network_topology_with_battery`.

# Decision rationale

Combine. Parametrize battery configs if reducing tests.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_validate_network_topology_with_battery`.
