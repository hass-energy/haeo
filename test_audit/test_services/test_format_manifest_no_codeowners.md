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
  nodeid: tests/test_services.py::test_format_manifest_no_codeowners
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_format_manifest_no_codeowners
  fixtures: []
  markers: []
notes:
  behavior: Leaves manifests without codeowners unchanged.
  redundancy: Related to codeowner normalization but distinct case.
  decision_rationale: Keep. Ensures missing field is handled safely.
---

# Behavior summary

Confirms `_format_manifest` does not alter manifests lacking codeowners.

# Redundancy / overlap

No overlap with codeowner normalization test.

# Decision rationale

Keep. Missing fields should be preserved.

# Fixtures / setup

Uses a manifest stub.

# Next actions

None.
