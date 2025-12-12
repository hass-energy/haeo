"""Config flow for Home Assistant Energy Optimizer integration."""

from .flows.hub import HubConfigFlow

# Main config flow class for the integration
# Subentry flows are registered via HubConfigFlow.async_get_supported_subentry_types()
# This is the standard Home Assistant pattern for exposing subentry flow types
HaeoConfigFlow = HubConfigFlow
