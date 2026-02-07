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
      behavior: Reconfigure renames grid element.
      redundancy: Per-element rename coverage.
    - id: load
      reviewed: true
      decision: keep
      behavior: Reconfigure renames load element.
      redundancy: Per-element rename coverage.
    - id: inverter
      reviewed: true
      decision: keep
      behavior: Reconfigure renames inverter element.
      redundancy: Per-element rename coverage.
    - id: solar
      reviewed: true
      decision: keep
      behavior: Reconfigure renames solar element.
      redundancy: Per-element rename coverage.
    - id: battery
      reviewed: true
      decision: keep
      behavior: Reconfigure renames battery element.
      redundancy: Per-element rename coverage.
    - id: connection
      reviewed: true
      decision: keep
      behavior: Reconfigure renames connection element.
      redundancy: Per-element rename coverage.
    - id: node
      reviewed: true
      decision: keep
      behavior: Reconfigure renames node element.
      redundancy: Per-element rename coverage.
    - id: battery_section
      reviewed: true
      decision: keep
      behavior: Reconfigure renames battery_section element.
      redundancy: Per-element rename coverage.
meta:
  nodeid: tests/flows/test_element_flows.py::test_element_flow_reconfigure_rename
  source_file: tests/flows/test_element_flows.py
  test_class: ''
  test_function: test_element_flow_reconfigure_rename
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure updates titles when element names change.
  redundancy: End-to-end rename coverage.
  decision_rationale: Keep. Ensures renames persist.
---

# Behavior summary

Reconfigure updates element names across types.

# Redundancy / overlap

Broad coverage across elements.

# Decision rationale

Keep. Prevents rename regressions.

# Fixtures / setup

Uses existing subentries and flow helpers.

# Next actions

None.
