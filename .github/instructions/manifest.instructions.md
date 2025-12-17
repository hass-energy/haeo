---
applyTo: '**/manifest.json'
description: Manifest.json requirements
globs: ['**/manifest.json']
alwaysApply: false
---

# Manifest requirements

The manifest.json defines integration metadata for Home Assistant.
When this instruction activates, the current manifest content is visible for reference.

## Required fields

All integrations must include:

- **domain**: Integration domain name (lowercase, underscores only)
- **name**: Human-readable display name
- **codeowners**: GitHub usernames with `@` prefix for notification
- **integration_type**: Integration category (hub, device, service, etc.)
- **documentation**: URL to documentation
- **requirements**: Python package dependencies with version constraints
- **version**: Semantic version string (MAJOR.MINOR.PATCH)

## Config flow

Set `config_flow: true` when the integration has UI-based configuration.
This enables the integration to appear in the "Add Integration" dialog.

## IoT class

The `iot_class` describes how the integration communicates:

- `local_push` - Local network with push updates (preferred for local devices)
- `local_polling` - Local network with polling
- `cloud_push` - Cloud service with push updates
- `cloud_polling` - Cloud service with polling
- `calculated` - No external data, purely calculated values

Choose the class that best represents the primary data source.

## Dependencies

List other Home Assistant integrations this integration depends on.
Use an empty array if there are no dependencies.

## HACS compatibility

For HACS distribution:

- Version field must be present and follow semantic versioning
- Requirements must use valid PyPI package names
- Documentation URL must be accessible
- Issue tracker URL is recommended
