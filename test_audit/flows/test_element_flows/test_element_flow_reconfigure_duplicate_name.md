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
      behavior: Duplicate name rejected on reconfigure for grid.
      redundancy: Per-element validation coverage.
    - id: load
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected on reconfigure for load.
      redundancy: Per-element validation coverage.
    - id: inverter
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected on reconfigure for inverter.
      redundancy: Per-element validation coverage.
    - id: solar
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected on reconfigure for solar.
      redundancy: Per-element validation coverage.
    - id: battery
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected on reconfigure for battery.
      redundancy: Per-element validation coverage.
    - id: connection
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected on reconfigure for connection.
      redundancy: Per-element validation coverage.
    - id: node
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected on reconfigure for node.
      redundancy: Per-element validation coverage.
    - id: battery_section
      reviewed: true
      decision: keep
      behavior: Duplicate name rejected on reconfigure for battery_section.
      redundancy: Per-element validation coverage.
meta:
  nodeid: tests/flows/test_element_flows.py::test_element_flow_reconfigure_duplicate_name
  source_file: tests/flows/test_element_flows.py
  test_class: ''
  test_function: test_element_flow_reconfigure_duplicate_name
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure rejects duplicate names across element types.
  redundancy: End-to-end validation coverage.
  decision_rationale: Keep. Ensures name uniqueness during reconfigure.
---

# Behavior summary

Reconfigure rejects duplicate names for all elements.

# Redundancy / overlap

Broad validation coverage across elements.

# Decision rationale

Keep. Prevents duplicate names on update.

# Fixtures / setup

Uses multiple subentries and flow helpers.

# Next actions

None.
