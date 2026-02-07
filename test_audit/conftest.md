---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
meta:
  source_file: /Users/trenthouliston/Code/gaeo/tests/conftest.py
  fixtures:
    - element_test_data
    - configure_logging
    - auto_enable_custom_integrations
notes:
  behavior: Provides session-level element flow test data, logging configuration, and integration enablement for all tests.
  redundancy: No redundancy detected; fixtures serve distinct purposes.
  decision_rationale: Keep. These fixtures are foundational for test data loading and clean test output.
---

# Fixture summary

Defines session fixtures for dynamic flow test data and logging, plus an autouse fixture to enable custom integrations.

# Usage and scope

- element_test_data (session): loads flow test cases for all elements.
- configure_logging (session, autouse): reduces HA log noise.
- auto_enable_custom_integrations (autouse): enables custom integrations for all tests.

# Redundancy / overlap

No overlap identified.

# Decision rationale

Keep. These fixtures provide critical shared setup for the test suite.

# Next actions

None.
