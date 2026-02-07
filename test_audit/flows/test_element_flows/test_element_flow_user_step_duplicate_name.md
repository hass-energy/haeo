---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: grid
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected for grid.
      redundancy: Per-element validation coverage.
    - id: load
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected for load.
      redundancy: Per-element validation coverage.
    - id: inverter
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected for inverter.
      redundancy: Per-element validation coverage.
    - id: solar
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected for solar.
      redundancy: Per-element validation coverage.
    - id: battery
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected for battery.
      redundancy: Per-element validation coverage.
    - id: connection
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected for connection.
      redundancy: Per-element validation coverage.
    - id: node
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected for node.
      redundancy: Per-element validation coverage.
    - id: battery_section
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected for battery_section.
      redundancy: Per-element validation coverage.
meta:
  nodeid: tests/flows/test_element_flows.py::test_element_flow_user_step_duplicate_name
  source_file: tests/flows/test_element_flows.py
  test_class: ''
  test_function: test_element_flow_user_step_duplicate_name
  fixtures: []
  markers: []
notes:
  behavior: Duplicate names yield validation errors across element types.
  redundancy: End-to-end validation coverage.
  decision_rationale: Keep. Ensures unique names per hub.
---

# Behavior summary

User step rejects duplicate names for all element types.

# Redundancy / overlap

Broad validation coverage across elements.

# Decision rationale

Keep. Prevents duplicate elements.

# Fixtures / setup

Uses existing subentries and flow helpers.

# Next actions

None.
