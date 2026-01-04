"""Energy storage element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model import energy_storage as model_storage
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData

from .flow import EnergyStorageSubentryFlowHandler
from .schema import CONF_CAPACITY, CONF_INITIAL_CHARGE, ELEMENT_TYPE, EnergyStorageConfigData, EnergyStorageConfigSchema

type EnergyStorageOutputName = Literal[
    "energy_storage_power_charge",
    "energy_storage_power_discharge",
    "energy_storage_power_active",
    "energy_storage_energy_stored",
    "energy_storage_power_balance",
    "energy_storage_energy_in_flow",
    "energy_storage_energy_out_flow",
    "energy_storage_soc_max",
    "energy_storage_soc_min",
]

ENERGY_STORAGE_OUTPUT_NAMES: Final[frozenset[EnergyStorageOutputName]] = frozenset(
    (
        ENERGY_STORAGE_POWER_CHARGE := "energy_storage_power_charge",
        ENERGY_STORAGE_POWER_DISCHARGE := "energy_storage_power_discharge",
        ENERGY_STORAGE_POWER_ACTIVE := "energy_storage_power_active",
        ENERGY_STORAGE_ENERGY_STORED := "energy_storage_energy_stored",
        ENERGY_STORAGE_POWER_BALANCE := "energy_storage_power_balance",
        ENERGY_STORAGE_ENERGY_IN_FLOW := "energy_storage_energy_in_flow",
        ENERGY_STORAGE_ENERGY_OUT_FLOW := "energy_storage_energy_out_flow",
        ENERGY_STORAGE_SOC_MAX := "energy_storage_soc_max",
        ENERGY_STORAGE_SOC_MIN := "energy_storage_soc_min",
    )
)

type EnergyStorageDeviceName = Literal["energy_storage"]

ENERGY_STORAGE_DEVICE_NAMES: Final[frozenset[EnergyStorageDeviceName]] = frozenset(
    (ENERGY_STORAGE_DEVICE := "energy_storage",),
)


class EnergyStorageAdapter:
    """Adapter for Energy Storage elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = EnergyStorageSubentryFlowHandler
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def available(self, config: EnergyStorageConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if energy storage configuration can be loaded."""
        ts_loader = TimeSeriesLoader()

        # Check required time series fields
        required_fields = [CONF_CAPACITY, CONF_INITIAL_CHARGE]
        return all(ts_loader.available(hass=hass, value=config[field]) for field in required_fields)

    async def load(
        self,
        config: EnergyStorageConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> EnergyStorageConfigData:
        """Load energy storage configuration values from sensors."""
        ts_loader = TimeSeriesLoader()

        capacity = await ts_loader.load(hass=hass, value=config[CONF_CAPACITY], forecast_times=forecast_times)
        initial_charge = await ts_loader.load(
            hass=hass, value=config[CONF_INITIAL_CHARGE], forecast_times=forecast_times
        )

        return {
            "element_type": config["element_type"],
            "name": config["name"],
            "capacity": capacity,
            "initial_charge": initial_charge,
        }

    def create_model_elements(self, config: EnergyStorageConfigData) -> list[dict[str, Any]]:
        """Create model elements for EnergyStorage configuration.

        Direct pass-through to the model energy storage element.
        """
        return [
            {
                "element_type": "energy_storage",
                "name": config["name"],
                "capacity": config["capacity"],
                "initial_charge": config["initial_charge"][0],
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        _config: EnergyStorageConfigData,
    ) -> Mapping[EnergyStorageDeviceName, Mapping[EnergyStorageOutputName, OutputData]]:
        """Map model outputs to energy storage output names."""
        storage_data = model_outputs[name]

        storage_outputs: dict[EnergyStorageOutputName, OutputData] = {}

        # Power outputs
        storage_outputs[ENERGY_STORAGE_POWER_CHARGE] = replace(
            storage_data[model_storage.ENERGY_STORAGE_POWER_CHARGE], type=OutputType.POWER
        )
        storage_outputs[ENERGY_STORAGE_POWER_DISCHARGE] = replace(
            storage_data[model_storage.ENERGY_STORAGE_POWER_DISCHARGE], type=OutputType.POWER
        )

        # Active power (discharge - charge)
        charge_values = storage_data[model_storage.ENERGY_STORAGE_POWER_CHARGE].values
        discharge_values = storage_data[model_storage.ENERGY_STORAGE_POWER_DISCHARGE].values
        storage_outputs[ENERGY_STORAGE_POWER_ACTIVE] = replace(
            storage_data[model_storage.ENERGY_STORAGE_POWER_CHARGE],
            values=[d - c for c, d in zip(charge_values, discharge_values, strict=True)],
            direction=None,
            type=OutputType.POWER,
        )

        # Energy stored
        storage_outputs[ENERGY_STORAGE_ENERGY_STORED] = storage_data[model_storage.ENERGY_STORAGE_ENERGY_STORED]

        # Shadow prices
        if model_storage.ENERGY_STORAGE_POWER_BALANCE in storage_data:
            storage_outputs[ENERGY_STORAGE_POWER_BALANCE] = storage_data[model_storage.ENERGY_STORAGE_POWER_BALANCE]
        if model_storage.ENERGY_STORAGE_ENERGY_IN_FLOW in storage_data:
            storage_outputs[ENERGY_STORAGE_ENERGY_IN_FLOW] = storage_data[model_storage.ENERGY_STORAGE_ENERGY_IN_FLOW]
        if model_storage.ENERGY_STORAGE_ENERGY_OUT_FLOW in storage_data:
            storage_outputs[ENERGY_STORAGE_ENERGY_OUT_FLOW] = storage_data[
                model_storage.ENERGY_STORAGE_ENERGY_OUT_FLOW
            ]
        if model_storage.ENERGY_STORAGE_SOC_MAX in storage_data:
            storage_outputs[ENERGY_STORAGE_SOC_MAX] = storage_data[model_storage.ENERGY_STORAGE_SOC_MAX]
        if model_storage.ENERGY_STORAGE_SOC_MIN in storage_data:
            storage_outputs[ENERGY_STORAGE_SOC_MIN] = storage_data[model_storage.ENERGY_STORAGE_SOC_MIN]

        return {ENERGY_STORAGE_DEVICE: storage_outputs}


adapter = EnergyStorageAdapter()
