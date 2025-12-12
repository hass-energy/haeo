# Removing HAEO

This guide explains how to completely remove the Home Assistant Energy Optimizer (HAEO) integration from your system.

## Removal process (HACS installation)

HAEO is distributed as a HACS custom component, so its files remain on disk after you remove the integration from the Home Assistant UI. Follow the full sequence below to ensure everything is deleted. The steps mirror the [official HACS removal guidance](https://hacs.xyz/docs/basic/operations/#uninstall-remove):

1. Open **Settings** → **Devices & Services**.
2. Locate **"Home Assistant Energy Optimizer"**, open the **three-dot menu** (⋮), and choose **Delete**. Confirm the prompt.
3. Restart Home Assistant so the config entry unloads cleanly.
4. After Home Assistant restarts, delete the `/custom_components/haeo/` directory using the File Editor add-on, SSH, or Samba.
5. Restart Home Assistant again to make sure the component is fully removed and caches are cleared.

Only after the second restart are both the integration configuration and the installed files removed.

## What gets deleted

When you remove HAEO, the following items are automatically deleted:

- **Configuration entries**: The hub entry and all element subentries (batteries, grids, loads, generators)
- **Entities**: All sensors including:
    - Power sensors for each element
    - Energy sensors for storage elements
    - State of charge (SOC) sensors for batteries
    - Optimization cost sensor
    - Optimization status sensor
    - Optimization duration sensor
- **Devices**: All device registry entries for the hub and elements
- **Runtime data**: Current optimization state and results

## What is preserved

The following data remains in your system after removal:

- **Historical sensor data**: All historical state data stored in the Home Assistant recorder database remains available
- **Automations**: Any automations that reference HAEO entities will remain but become unavailable (their entities will show as "unavailable")
- **Dashboard cards**: Dashboard cards showing HAEO sensors will display "Entity not available" until removed

## Post-removal cleanup

After removing HAEO, you may want to clean up related items:

### Remove orphaned automations

1. Navigate to **Settings** → **Automations & Scenes**
2. Search for automations that reference HAEO entities
3. Edit or delete these automations as needed

### Remove dashboard cards

1. Edit your dashboards (click the three-dot menu → **Edit Dashboard**)
2. Remove any cards that displayed HAEO sensors
3. Save your changes

### Clear historical data (optional)

If you want to remove historical sensor data from the database:

1. Navigate to **Settings** → **System** → **Repairs**
2. Look for any HAEO-related issues and resolve them
3. To completely purge historical data, use the **Developer Tools** → **Services**:
    ```yaml
    service: recorder.purge_entities
    data:
      entity_id:
        - sensor.haeo_*  # This will purge all HAEO sensors
    ```

**Warning**: Purging historical data is permanent and cannot be undone.

## Manual cleanup (if needed)

If the integration was removed while in a bad state or the directory deletion failed, you may need to manually clean up:

### Check for orphaned devices and entities

1. Navigate to **Settings** → **Devices & Services** → **Devices**.
2. Search for device names that contained HAEO elements; delete any remaining entries.
3. Switch to the **Entities** tab, enable **Show unavailable entities**, and remove any lingering `sensor.haeo_*` entries.

## Reinstalling HAEO

If you want to reinstall HAEO after removing it:

1. The integration can be re-added through the normal installation process
2. Your previous configuration will not be restored automatically
3. You will need to reconfigure your energy system from scratch
4. Historical data from the previous installation will remain in the database with orphaned entity IDs

## Troubleshooting removal

If you encounter issues removing HAEO:

### Integration still appears in HACS

1. Open **HACS** → **Integrations** and ensure HAEO is no longer listed under **Installed**.
2. If it is, click the entry and choose **Uninstall**. HACS may prompt you to restart; accept the prompt.

### Files reappear after deletion

1. Verify that no automated backups or version control restores the directory.
2. Restart Home Assistant and re-check `/custom_components/haeo/`.
3. If the directory keeps returning, review your Supervisor add-ons or deployment pipeline for sync jobs that re-deploy the integration.

### Errors remain in logs

1. After the final restart, open **Settings** → **System** → **Logs**.
2. Clear HAEO-related issues from **Settings** → **System** → **Repairs**.
3. If errors persist, reinstall HAEO via HACS, confirm the integration loads, then repeat the removal steps.

## Getting help

If you continue to experience issues removing HAEO:

1. Check the [HACS documentation](https://hacs.xyz/docs/basic/operations/#uninstall-remove) for the latest uninstall notes
2. Review the [HAEO GitHub Issues](https://github.com/hass-energy/haeo/issues)
3. Create a new issue with:
    - Home Assistant version
    - HAEO version
    - Description of the removal issue
    - Relevant error logs
    - Steps you've already tried
