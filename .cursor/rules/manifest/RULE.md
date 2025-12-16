---
description: "Manifest.json requirements"
globs: ["**/manifest.json"]
alwaysApply: false
---

# Manifest requirements

## Required fields

Every `manifest.json` must include:

```json
{
  "domain": "haeo",
  "name": "HAEO",
  "codeowners": ["@username"],
  "integration_type": "hub",
  "documentation": "https://github.com/hass-energy/haeo",
  "requirements": ["pulp>=2.7.0"],
  "version": "1.0.0"
}
```

## Field descriptions

- **domain**: Integration domain name (lowercase, underscores)
- **name**: Human-readable name
- **codeowners**: GitHub usernames with `@` prefix
- **integration_type**: One of `device`, `hub`, `service`, `system`, `helper`
- **documentation**: URL to documentation
- **requirements**: Python package dependencies with version constraints
- **version**: Semantic version string

## Config flow

If integration has UI configuration:

```json
{
  "config_flow": true
}
```

## IoT class

Specify connectivity method:

```json
{
  "iot_class": "local_polling"
}
```

Options:
- `cloud_polling` - Cloud service, polling
- `cloud_push` - Cloud service, push updates
- `local_polling` - Local network, polling
- `local_push` - Local network, push updates
- `calculated` - No external data, calculated values
- `assumed_state` - State is assumed, not confirmed

## Dependencies

For integrations that depend on other integrations:

```json
{
  "dependencies": ["other_integration"]
}
```

## HACS compatibility

For HACS distribution, ensure:
- Version field is present
- Requirements use valid PyPI package names
- Documentation URL is accessible
