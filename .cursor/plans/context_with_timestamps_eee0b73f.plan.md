---
name: Context with Timestamps
overview: Update OptimizationContext to store injectable timestamps (init_timestamp and reference_timestamp) alongside hub_config, participant schemas, and source states for full reproducibility.
todos:
  - id: store-init-timestamp
    content: Store init_timestamp in coordinator during async_initialize()
    status: pending
  - id: update-context-dataclass
    content: Add hub_config, init_timestamp, reference_timestamp; remove forecast_timestamps
    status: pending
  - id: update-build-method
    content: Update build() to accept new parameters
    status: pending
  - id: update-call-site
    content: Update coordinator to pass all required data to build()
    status: pending
  - id: update-consumers
    content: Update code that reads forecast_timestamps to derive it
    status: pending
---
