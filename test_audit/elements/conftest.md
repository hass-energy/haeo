---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
meta:
  source_file: /Users/trenthouliston/Code/gaeo/tests/elements/conftest.py
  fixtures:
    - hub_entry
notes:
  behavior: Defines shared helpers for element flow tests, including hub entry fixture and HA state helpers.
  redundancy: Helper functions are specific to element flow tests; no overlap with other conftest modules.
  decision_rationale: Keep. These helpers reduce repetition across element flow tests.
---

# Fixture summary

Provides a hub entry fixture and helper functions for creating flows, adding participants, and setting sensor states.

# Usage and scope

- hub_entry: minimal hub entry with advanced mode enabled.
- create_flow/add_participant/set_sensor/set_forecast_sensor: shared helpers for flow tests.

# Redundancy / overlap

No redundancy identified.

# Decision rationale

Keep. Fixture and helpers are necessary for clean element test setup.

# Next actions

None.
