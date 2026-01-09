"""Network element adapter for model layer integration.

The Network element is special: it represents the optimization network itself
rather than a physical device. It is auto-created (not manually configurable)
and provides network-level outputs like optimization cost, status, and duration.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.model import (
    NETWORK_OPTIMIZATION_COST,
    NETWORK_OPTIMIZATION_DURATION,
    NETWORK_OPTIMIZATION_STATUS,
    ModelOutputName,
    NetworkOutputName,
)
from custom_components.haeo.model.output_data import OutputData

from .schema import ELEMENT_TYPE, NetworkConfigData, NetworkConfigSchema

# Re-export the output names from model layer
NETWORK_OUTPUT_NAMES: Final[frozenset[NetworkOutputName]] = frozenset(
    (NETWORK_OPTIMIZATION_COST, NETWORK_OPTIMIZATION_STATUS, NETWORK_OPTIMIZATION_DURATION)
)

# Device name for network element
type NetworkDeviceName = Literal["network"]

NETWORK_DEVICE_NAMES: Final[frozenset[NetworkDeviceName]] = frozenset(
    (NETWORK_DEVICE_NETWORK := "network",),
)


class NetworkSubentryFlowHandler:
    """Stub flow handler for network element.

    Network elements are auto-created and cannot be manually configured.
    This class exists to satisfy the ElementAdapter protocol but raises
    NotImplementedError if instantiated.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Raise error - network elements cannot be manually configured."""
        msg = "Network elements are auto-created and cannot be manually configured"
        raise NotImplementedError(msg)


class NetworkAdapter:
    """Adapter for Network elements.

    The Network adapter is unique in that:
    - It is auto-created (never shown in the element type selector)
    - It creates no model elements (the network IS the model)
    - Its outputs come from the model Network.outputs() method
    """

    element_type: str = ELEMENT_TYPE
    flow_class: type = NetworkSubentryFlowHandler
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER

    def available(self, config: NetworkConfigSchema, **_kwargs: Any) -> bool:
        """Check if network configuration can be loaded.

        Network is always available since it has no external dependencies.
        """
        _ = config  # Unused but required by protocol
        return True

    async def load(
        self,
        config: NetworkConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> NetworkConfigData:
        """Load network configuration values.

        Network has no sensor-loaded values, so this is a pass-through.
        """
        _ = hass, forecast_times  # Unused but required by protocol
        return {
            "element_type": config["element_type"],
            "name": config["name"],
        }

    def model_elements(self, config: NetworkConfigData) -> list[dict[str, Any]]:
        """Return model element parameters for Network configuration.

        Network doesn't create any model elements - it IS the model container.
        """
        _ = config  # Unused
        return []

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        _config: NetworkConfigData,
    ) -> Mapping[NetworkDeviceName, Mapping[NetworkOutputName, OutputData]]:
        """Convert model outputs to network adapter outputs.

        The network outputs are stored under the special key "network" in model_outputs,
        populated directly from Network.outputs() by the coordinator.
        """
        _ = name  # Network name not used for output lookup

        # Network outputs come from the "network" key in model_outputs
        network_model_outputs = model_outputs.get("network", {})

        network_outputs: dict[NetworkOutputName, OutputData] = {}

        if NETWORK_OPTIMIZATION_COST in network_model_outputs:
            network_outputs[NETWORK_OPTIMIZATION_COST] = network_model_outputs[NETWORK_OPTIMIZATION_COST]

        if NETWORK_OPTIMIZATION_STATUS in network_model_outputs:
            network_outputs[NETWORK_OPTIMIZATION_STATUS] = network_model_outputs[NETWORK_OPTIMIZATION_STATUS]

        if NETWORK_OPTIMIZATION_DURATION in network_model_outputs:
            network_outputs[NETWORK_OPTIMIZATION_DURATION] = network_model_outputs[NETWORK_OPTIMIZATION_DURATION]

        return {NETWORK_DEVICE_NETWORK: network_outputs}


adapter = NetworkAdapter()
