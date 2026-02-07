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
      behavior: Reconfigure succeeds for grid with unchanged data.
      redundancy: Per-element reconfigure coverage.
    - id: load
      reviewed: true
      decision: keep
      behavior: Reconfigure succeeds for load with unchanged data.
      redundancy: Per-element reconfigure coverage.
    - id: inverter
      reviewed: true
      decision: keep
      behavior: Reconfigure succeeds for inverter with unchanged data.
      redundancy: Per-element reconfigure coverage.
    - id: solar
      reviewed: true
      decision: keep
      behavior: Reconfigure succeeds for solar with unchanged data.
      redundancy: Per-element reconfigure coverage.
    - id: battery
      reviewed: true
      decision: keep
      behavior: Reconfigure succeeds for battery with unchanged data.
      redundancy: Per-element reconfigure coverage.
    - id: connection
      reviewed: true
      decision: keep
      behavior: Reconfigure succeeds for connection with unchanged data.
      redundancy: Per-element reconfigure coverage.
    - id: node
      reviewed: true
      decision: keep
      behavior: Reconfigure succeeds for node with unchanged data.
      redundancy: Per-element reconfigure coverage.
    - id: battery_section
      reviewed: true
      decision: keep
      behavior: Reconfigure succeeds for battery_section with unchanged data.
      redundancy: Per-element reconfigure coverage.
meta:
  nodeid: tests/flows/test_element_flows.py::test_element_flow_reconfigure_success
  source_file: tests/flows/test_element_flows.py
  test_class: ''
  test_function: test_element_flow_reconfigure_success
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure submits unchanged data successfully across element types.
  redundancy: End-to-end reconfigure coverage.
  decision_rationale: Keep. Ensures reconfigure path works.
---

# Behavior summary

Reconfigure accepts unchanged data for all element types.

# Redundancy / overlap

Broad coverage across elements.

# Decision rationale

Keep. Prevents reconfigure regressions.

# Fixtures / setup

Uses existing subentries and flow helpers.

# Next actions

None.
