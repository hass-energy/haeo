# Installation

This guide will walk you through installing HAEO on your Home Assistant instance.

## Prerequisites

Before installing HAEO, ensure you have:

- **Home Assistant** version 2025.4.4 or newer
- **HACS** (Home Assistant Community Store) installed (recommended)
- **Linear Programming Solver**: HiGHS solver is included with PuLP (no additional setup needed)

!!! info "Solver Information"
    HAEO uses the [PuLP](https://github.com/coin-or/pulp) library for linear programming, which includes the HiGHS solver by default. No additional solver installation is required for basic usage.

## Method 1: HACS Installation (Recommended)

HACS provides automatic updates and easy installation.

### Step 1: Add Custom Repository

1. Open your Home Assistant instance
2. Navigate to **HACS** → **Integrations**
3. Click the three dots (⋮) in the top right corner
4. Select **Custom repositories**
5. Add the following details:
    - **Repository**: `https://github.com/ha-energy-optimiser/haeo`
    - **Category**: `Integration`
6. Click **Add**

### Step 2: Install HAEO

1. In HACS, search for **HAEO** or **Home Assistant Energy Optimization**
2. Click on the integration
3. Click **Download**
4. Select the latest version
5. Click **Download** again to confirm

### Step 3: Restart Home Assistant

After installation, restart Home Assistant:

1. Navigate to **Settings** → **System**
2. Click **Restart**
3. Wait for Home Assistant to fully restart (usually 1-2 minutes)

## Method 2: Manual Installation

If you prefer not to use HACS or need manual control:

### Step 1: Download HAEO

1. Visit the [releases page](https://github.com/ha-energy-optimiser/haeo/releases)
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
3. Search for **HAEO** or **Home Assistant Energy Optimization**

If HAEO appears in the list, the installation was successful!

## Next Steps

Now that HAEO is installed, you're ready to configure your first energy network:

[:octicons-arrow-right-24: Continue to Configuration](configuration.md)

## Advanced: Additional Solvers

While HiGHS (included with PuLP) is sufficient for most use cases, you can install additional solvers for potentially better performance on large problems:

!!! note "Optional Solvers"
    These are **optional** and only recommended for advanced users with large networks or long time horizons.

### CBC Solver

```bash
# Install CBC solver
pip install pulp[cbc]
```

### GLPK Solver

```bash
# Install GLPK solver
pip install pulp[glpk]
```

### SCIP Solver

```bash
# Install SCIP solver
pip install pulp[scip]
```

See the [LP Solvers reference](../reference/solvers.md) for detailed solver information.

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
    Always check the [release notes](https://github.com/ha-energy-optimiser/haeo/releases) before updating, especially for major version changes. Some updates may require configuration adjustments.

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

## Troubleshooting Installation

### HAEO Doesn't Appear in Integration List

- Ensure you restarted Home Assistant after installation
- Check the file permissions are correct (`haeo` directory should be readable)
- Review Home Assistant logs for error messages:
    ```
    Settings → System → Logs
    ```

### Import Errors

If you see import errors in the logs:

- Verify Python version is 3.13 or newer
- Ensure all dependencies installed correctly
- Try clearing the `__pycache__` directories:
    ```bash
    find custom_components/haeo -type d -name __pycache__ -exec rm -rf {} +
    ```

### Permission Errors

On some systems, file permissions may cause issues:

```bash
# Set correct permissions (from Home Assistant config directory)
chmod -R 755 custom_components/haeo
```

See the [troubleshooting page](troubleshooting.md) for more common issues and solutions.

