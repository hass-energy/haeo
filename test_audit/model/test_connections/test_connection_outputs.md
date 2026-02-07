---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: true
  cases:
    - id: connection_with_forward_flow_only
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: connection_with_reverse_flow_only
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: connection_respecting_forward_power_limit
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: connection_with_efficiency_losses
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: connection_with_transfer_pricing_and_power_flow
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: connection_with_time-varying_limits
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: connection_with_bidirectional_transfer_pricing_and_forward_flow
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: connection_with_bidirectional_efficiency_losses
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
    - id: connection_with_fixed_power_in_reverse_direction
      reviewed: true
      decision: keep
      behavior: Validates expected behavior for this case.
      redundancy: Complements other parameterized cases.
meta:
  nodeid: tests/model/test_connections.py::test_connection_outputs
  source_file: tests/model/test_connections.py
  test_class: ''
  test_function: test_connection_outputs
  fixtures: []
  markers: []
notes:
  behavior: Validates connection output values across flow/limit/pricing scenarios.
  redundancy: Broader than base property tests.
  decision_rationale: Keep. Ensures connection output correctness.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions
