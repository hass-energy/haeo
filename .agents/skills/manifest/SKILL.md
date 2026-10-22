---
name: manifest
description: Home Assistant manifest requirements for custom_components/haeo/manifest.json and hacs.json — required fields, key order, config_flow, iot_class, dependencies and after_dependencies, requirements, and HACS compatibility. Use when editing manifest.json or hacs.json, or changing integration metadata, requirements, dependencies, or version.
---

# Manifest requirements

[`custom_components/haeo/manifest.json`](../../../custom_components/haeo/manifest.json) defines integration metadata for Home Assistant.
Read it before changing it, and run hassfest afterwards as the `lint` skill describes.
Hassfest requires `domain` and `name` first and the remaining keys in alphabetical order.

## Required fields

All integrations must include:

- **domain**: Integration domain name (lowercase, underscores only)
- **name**: Human-readable display name
- **codeowners**: GitHub usernames with `@` prefix for notification
- **integration_type**: Integration category (hub, device, service, etc.)
- **documentation**: URL to documentation
- **requirements**: Python package dependencies with version constraints
- **version**: The release version, which must equal `version` in `pyproject.toml`; change it only through the `update-version` skill

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

`dependencies` lists integrations that must be set up before HAEO; use an empty array if there are none.
`after_dependencies` lists integrations HAEO uses when present and must load after, without requiring them.
Add an integration there when HAEO starts importing from it.

## HACS compatibility

For HACS distribution:

- Version field must be present
- Requirements must use valid PyPI package names
- `hacs.json` `homeassistant` is the minimum Home Assistant version and must equal the `homeassistant>=` pin in `pyproject.toml`; the version gate checks this
- Documentation URL must be accessible
- Issue tracker URL is recommended
