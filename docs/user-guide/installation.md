# Installation

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

This guide will walk you through installing HAEO on your Home Assistant instance.

## Prerequisites

Before installing HAEO, ensure you have:

- **Home Assistant** version 2026.1.1 or newer
- **[HACS](https://hacs.xyz/)** (Home Assistant Community Store) installed (recommended)

## Method 1: HACS installation (recommended)

HAEO is published in the [default HACS store](https://github.com/hacs/default).
You do not need to [add a custom repository](https://hacs.xyz/docs/faq/custom_repositories/).
HACS provides automatic updates after installation.

For the general download workflow, see the [HACS dashboard documentation](https://hacs.xyz/docs/use/repositories/dashboard/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hass-energy&repository=haeo&category=integration)

### Step 1: Install HAEO

1. Open your Home Assistant instance
2. Open **HACS** from the sidebar
3. Go to **Integrations**
4. Search for **HAEO** or **Home Assistant Energy Optimizer**
5. Open the repository entry and select **Download** (see [downloading a repository](https://hacs.xyz/docs/use/repositories/dashboard/#downloading-a-repository) in the HACS docs)
6. Confirm the latest version

You can also use the [My Home Assistant](https://my.home-assistant.io/) link above to open HAEO directly in HACS.

### Step 2: Restart Home Assistant

After installation, restart Home Assistant:

1. Navigate to **Settings** → **System**
2. Click **Restart**
3. Wait for Home Assistant to complete the restart before proceeding

If you need a refresher on the restart process, see the [Home Assistant restart documentation](https://www.home-assistant.io/docs/configuration/troubleshooting/#restarting-home-assistant).

## Method 2: Manual Installation

If you prefer not to use HACS or need manual control:

### Step 1: Download HAEO

1. Visit the [releases page](https://github.com/hass-energy/haeo/releases)
2. Download the latest `haeo.zip` file
3. Extract the archive

### Step 2: Copy Files

1. Connect to your Home Assistant instance (via SSH, Samba, or file editor)
2. Navigate to your Home Assistant config directory (usually `/config`)
3. If it doesn't exist, create a `custom_components` directory
4. Copy the `haeo` folder from the archive into `custom_components`

Your directory structure should look like:

```
config/
├── custom_components/
│   └── haeo/
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       └── ... (other files)
└── configuration.yaml
```

### Step 3: Restart Home Assistant

Restart Home Assistant as described in the HACS installation section.

## Verify Installation

After restarting, verify HAEO is installed correctly:

1. Navigate to **Settings** → **Devices & Services**
2. Click **Add Integration** (+ button in bottom right)
3. Search for **HAEO** or **Home Assistant Energy Optimizer**

If HAEO appears in the list, the installation was successful!

## Updating HAEO

### Via HACS

1. Open HACS → Integrations
2. Find HAEO in your installed integrations
3. If an update is available, click **Update**
4. Restart Home Assistant

### Manual Update

1. Download the latest release
2. Replace the `custom_components/haeo` directory with the new version
3. Restart Home Assistant

!!! warning "Breaking Changes"

    Always check the [release notes](https://github.com/hass-energy/haeo/releases) before updating.
    Pay special attention to major version changes.
    Some updates may require configuration adjustments.

See the [troubleshooting page](troubleshooting.md) for help with common installation issues.

## Uninstalling HAEO

### Remove the Integration

1. Navigate to **Settings** → **Devices & Services**
2. Find the HAEO integration
3. Click the three dots (⋮) next to it
4. Select **Delete**
5. Confirm deletion

### Remove Files

Via HACS:

1. Open HACS → Integrations
2. Find HAEO
3. Click the three dots (⋮)
4. Select **Remove**
5. Restart Home Assistant

Manual removal:

1. Delete the `custom_components/haeo` directory
2. Restart Home Assistant

## Next steps

Move on to these topics once the integration is installed.

<div class="grid cards" markdown>

- :material-cog-outline:{ .lg .middle } __Configure your first network__

    Create your hub, add elements, and establish energy flow connections.

    [:material-arrow-right: Configuration guide](configuration.md)

- :material-chart-line:{ .lg .middle } __Check optimization outputs__

    Learn how to read HAEO sensors and verify results after setup.

    [:material-arrow-right: Optimization overview](optimization.md)

- :material-bug-outline:{ .lg .middle } __Troubleshoot installation issues__

    Resolve common installation and startup problems quickly.

    [:material-arrow-right: Troubleshooting tips](troubleshooting.md)

</div>
