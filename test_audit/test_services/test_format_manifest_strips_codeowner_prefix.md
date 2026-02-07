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
  nodeid: tests/test_services.py::test_format_manifest_strips_codeowner_prefix
  source_file: tests/test_services.py
  test_class: ''
  test_function: test_format_manifest_strips_codeowner_prefix
  fixtures: []
  markers: []
notes:
  behavior: Strips @ prefix from codeowners without mutating the original manifest.
  redundancy: Distinct from no-codeowners case.
  decision_rationale: Keep. Validates codeowner normalization.
---

# Behavior summary

Ensures codeowner handles are stripped of @ and input manifest remains unchanged.

# Redundancy / overlap

No overlap with no-codeowners test.

# Decision rationale

Keep. Normalization behavior is important.

# Fixtures / setup

Uses a manifest stub.

# Next actions

None.
