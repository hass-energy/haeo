"""Tests for building coordinator outputs from an optimization's results."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import (
    Any,  # noqa: TID251  # Mock-typed test doubles (MagicMock spec=) and monkeypatched callback stand-ins
    Literal,
)
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
import numpy as np
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import (
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
)
from custom_components.haeo.coordinator import (
    ForecastPoint,
    HaeoDataUpdateCoordinator,
    build_coordinator_output,
    detect_currency_symbol,
    forecast_datetimes,
    price_currency_sources,
)
from custom_components.haeo.core.adapters.elements.battery import BATTERY_DEVICE_BATTERY, BATTERY_POWER_CHARGE
from custom_components.haeo.core.adapters.elements.connection import CONNECTION_DEVICE_CONNECTION, CONNECTION_POWER
from custom_components.haeo.core.adapters.elements.solar import SOLAR_POWER
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.data.loader.extractors.haeo import InterpolationMode
from custom_components.haeo.core.model import Network, OutputData, OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.infeasibility import Relaxation, RowLabel
from custom_components.haeo.core.schema.elements.connection import CONF_SOURCE, CONF_TARGET, SECTION_ENDPOINTS
from custom_components.haeo.core.schema.elements.grid import CONF_PRICE_SOURCE_TARGET
from custom_components.haeo.core.schema.sections import SECTION_EFFICIENCY, SECTION_POWER_LIMITS, SECTION_PRICING
from custom_components.haeo.core.units import currency_symbol
from custom_components.haeo.repairs import create_optimization_infeasible_issue, create_optimization_relaxed_issue

from .helpers import EARLIER_DIAGNOSTICS, EARLIER_ISSUE, mock_horizon, run_jobs_but, saved_diagnostics, source_state

_TIMES = tuple(datetime(2024, 6, 1, tzinfo=UTC) + timedelta(minutes=30 * i) for i in range(4))


@pytest.mark.usefixtures("mock_connection_subentry")
@pytest.mark.parametrize(
    ("conflicts", "relaxations", "relaxed_issue"),
    [
        pytest.param((), (), None, id="feasible"),
        pytest.param(
            (
                RowLabel("Test Grid:import", "power_limit_power_limit", 1),
                RowLabel("Switchboard", "element_power_balance", 1, balance=True),
                RowLabel("Test Grid:export", "power_limit_power_limit", 1),
            ),
            (
                Relaxation(RowLabel("Switchboard", "element_power_balance", 0, balance=True), -0.05),
                Relaxation(RowLabel("Switchboard", "element_power_balance", 1, balance=True), -0.25),
                Relaxation(RowLabel("Test Battery", "energy", None), 0.2),
            ),
            {"elements": "Test Grid, Switchboard", "minutes": "30", "relaxed_elements": "Switchboard, Test Battery"},
            id="relaxed",
        ),
        pytest.param(
            (),
            (Relaxation(RowLabel("Test Battery", "element_power_balance", 1, balance=True), 0.1),),
            {"elements": "Test Battery", "minutes": "30", "relaxed_elements": "Test Battery"},
            id="relaxed_without_conflicts",
        ),
    ],
)
async def test_async_update_data_returns_outputs(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
    conflicts: tuple[RowLabel, ...],
    relaxations: tuple[Relaxation, ...],
    relaxed_issue: dict[str, str] | None,
    tmp_path: Path,
) -> None:
    """Coordinator returns optimization results merged with element outputs, and reports any relaxed constraints."""
    hass.config.config_dir = str(tmp_path)
    fake_element = MagicMock()
    fake_element.outputs.return_value = {
        BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0, 2.0))
    }

    fake_network = MagicMock()
    fake_network.conflicts = conflicts
    fake_network.relaxations = relaxations
    if relaxed_issue is None:
        create_optimization_relaxed_issue(hass, mock_hub_entry.entry_id, EARLIER_ISSUE, EARLIER_DIAGNOSTICS)
    create_optimization_infeasible_issue(
        hass, mock_hub_entry.entry_id, "optimization_infeasible", EARLIER_ISSUE, EARLIER_DIAGNOSTICS
    )
    empty_element = MagicMock()
    empty_element.outputs.return_value = {}

    # Add connection element (config name is slugified to "battery_to_grid")
    fake_fwd_connection = MagicMock()
    fake_fwd_connection.outputs.return_value = {
        CONNECTION_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
    }
    fake_rev_connection = MagicMock()
    fake_rev_connection.outputs.return_value = {
        CONNECTION_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(0.3,), direction="+"),
    }

    fake_network.elements = {
        "Test Battery": fake_element,
        "empty": empty_element,
        "Battery to Grid:forward": fake_fwd_connection,
        "Battery to Grid:reverse": fake_rev_connection,
    }

    # Mock battery adapter
    mock_battery_adapter = MagicMock()
    mock_battery_adapter.outputs.return_value = {
        BATTERY_DEVICE_BATTERY: {BATTERY_POWER_CHARGE: OutputData(type=OutputType.POWER, unit="kW", values=(1.0, 2.0))}
    }

    generated_at = datetime(2024, 1, 1, 0, 15, tzinfo=UTC)
    # Round to nearest 30-minute period (00:15 rounds to 00:00), then add two 30-minute intervals
    base_timestamp = int(datetime(2024, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    expected_forecast_times = (base_timestamp, base_timestamp + 30 * 60, base_timestamp + 2 * 30 * 60)

    # Configure mock horizon manager with forecast timestamps
    mock_horizon(mock_runtime_data).get_forecast_timestamps.return_value = expected_forecast_times
    mock_horizon(mock_runtime_data).periods_seconds = [1800, 1800]

    # Mock connection adapter to return proper outputs
    mock_connection_adapter = MagicMock()
    mock_connection_adapter.outputs.return_value = {
        CONNECTION_DEVICE_CONNECTION: {
            CONNECTION_POWER: OutputData(type=OutputType.POWER, unit="kW", values=(0.5,), direction="+"),
        }
    }

    # Mock empty outputs for grid
    mock_empty_outputs = MagicMock(return_value={})

    # Create mock loaded configs (use subentry titles as keys)
    mock_loaded_configs = {
        "Test Battery": mock_battery_subentry.data,
        "Test Grid": mock_grid_subentry.data,
        "Battery to Grid": {
            CONF_ELEMENT_TYPE: "connection",
            CONF_NAME: "Battery to Grid",
            SECTION_ENDPOINTS: {
                CONF_SOURCE: "Test Battery",
                CONF_TARGET: "Test Grid",
            },
            SECTION_POWER_LIMITS: {},
            SECTION_PRICING: {},
            SECTION_EFFICIENCY: {},
        },
    }

    # Patch coordinator to use mocked _load_from_input_stores
    with (
        patch("custom_components.haeo.coordinator.coordinator.build_network"),
        patch.object(
            hass, "async_add_executor_job", side_effect=run_jobs_but(hass, fake_network.optimize, 123.45)
        ) as mock_executor,
        patch("custom_components.haeo.coordinator.coordinator.dt_util.utcnow", return_value=generated_at),
        patch.dict(
            ELEMENT_TYPES,
            {
                "battery": MagicMock(outputs=mock_battery_adapter.outputs),
                "grid": MagicMock(outputs=mock_empty_outputs),
                "connection": MagicMock(outputs=mock_connection_adapter.outputs),
            },
        ),
    ):
        coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
        # Set network directly (it's created in async_initialize in production)
        coordinator._network = fake_network

        # Mock the _load_from_input_stores method
        with patch.object(coordinator, "_load_from_input_stores", return_value=mock_loaded_configs):
            result = await coordinator._async_update_data()

    mock_executor.assert_any_call(fake_network.optimize)

    # Verify result is a CoordinatorData dataclass
    assert result.context is not None
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.completed_at >= result.started_at
    assert isinstance(result.outputs, dict)

    network_outputs = result.outputs["System"][ELEMENT_TYPE_NETWORK]
    cost_output = network_outputs[OUTPUT_NAME_OPTIMIZATION_COST]
    assert cost_output.type == OutputType.COST
    assert cost_output.unit == currency_symbol(hass.config.currency)
    assert cost_output.state == 123.45
    assert cost_output.forecast is None

    assert OUTPUT_NAME_OPTIMIZATION_STATUS not in network_outputs

    duration_output = network_outputs[OUTPUT_NAME_OPTIMIZATION_DURATION]
    assert duration_output.type == OutputType.DURATION
    assert duration_output.state is not None
    assert duration_output.forecast is None

    battery_outputs = result.outputs["Test Battery"][BATTERY_DEVICE_BATTERY]
    battery_output = battery_outputs[BATTERY_POWER_CHARGE]
    assert battery_output.type == OutputType.POWER
    assert battery_output.unit == "kW"
    assert battery_output.state == 1.0
    # Forecast should be list of ForecastPoint with datetime objects in local timezone
    local_tz = dt_util.get_default_time_zone()
    assert battery_output.forecast == [
        ForecastPoint(time=datetime.fromtimestamp(expected_forecast_times[0], tz=local_tz), value=1.0),
        ForecastPoint(time=datetime.fromtimestamp(expected_forecast_times[1], tz=local_tz), value=2.0),
    ]

    # A plan that is found leaves an earlier impossible plan for the user to resolve
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"optimization_infeasible_{mock_hub_entry.entry_id}") is not None
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"optimization_relaxed_{mock_hub_entry.entry_id}")
    assert issue is not None
    if relaxed_issue is None:
        # A plan that meets every constraint leaves an earlier relaxation for the user to resolve
        assert issue.translation_placeholders == {**EARLIER_ISSUE, "diagnostics": EARLIER_DIAGNOSTICS}
    else:
        relaxed_periods = str(len({r.row.period for r in relaxations if r.row.period is not None}))
        planned_at = f"{dt_util.as_local(dt_util.utc_from_timestamp(expected_forecast_times[0])):%Y-%m-%d %H:%M}"
        assert issue.translation_placeholders is not None
        diagnostics = saved_diagnostics(hass, issue.translation_placeholders["diagnostics"], "relaxed")
        assert issue.translation_placeholders == {
            **relaxed_issue,
            "relaxed_periods": relaxed_periods,
            "planned_at": planned_at,
            "diagnostics": issue.translation_placeholders["diagnostics"],
        }
        assert diagnostics["data"]["failure"] == {
            "conflicts": [str(row) for row in conflicts],
            "relaxations": [str(relaxation) for relaxation in relaxations],
        }


async def test_async_update_data_raises_on_missing_model_element(
    hass: HomeAssistant,
    mock_hub_entry: ConfigEntry,
    mock_battery_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coordinator should surface KeyError when adapter cannot find model element outputs."""

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    fake_network = Network(name="net", periods=np.array([1.0]))
    # Network must have at least one element for HiGHS to optimize (empty networks are rejected)
    fake_network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "dummy_node"})

    def broken_outputs(*_args: Any, **_kwargs: Any) -> dict[str, dict[str, OutputData]]:
        msg = "missing model element"
        raise KeyError(msg)

    patched_entry = MagicMock(outputs=broken_outputs)

    monkeypatch.setattr(
        "custom_components.haeo.coordinator.coordinator.ELEMENT_TYPES",
        {**ELEMENT_TYPES, "battery": patched_entry},
    )
    coordinator._network = fake_network

    with (
        patch.object(
            coordinator,
            "_load_from_input_stores",
            return_value={"Test Battery": mock_battery_subentry.data},
        ),
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, return_value=0.0),
        pytest.raises(KeyError),
    ):
        await coordinator._async_update_data()


@pytest.mark.parametrize(
    ("values", "state_last", "times", "state", "forecast", "interpolation_mode"),
    [
        pytest.param((1.0, 2.0, 3.0, 4.0), False, 4, 1.0, (1.0, 2.0, 3.0, 4.0), None, id="boundary_values"),
        pytest.param((1.0, 2.0), False, 3, 1.0, (1.0, 2.0), InterpolationMode.PREVIOUS, id="interval_values"),
        pytest.param((1.0, 2.0, 3.0), True, 3, 3.0, (1.0, 2.0, 3.0), None, id="state_last"),
        pytest.param((5.0,), False, 2, 5.0, None, None, id="single_value"),
        pytest.param((), False, 2, None, None, None, id="no_values"),
    ],
)
def test_build_coordinator_output_state_and_forecast(
    values: tuple[float, ...],
    state_last: bool,
    times: int,
    state: float | None,
    forecast: tuple[float, ...] | None,
    interpolation_mode: InterpolationMode | None,
) -> None:
    """Interval values take the first n of the n+1 boundary times and hold until the next; boundary values take all."""
    output = build_coordinator_output(
        SOLAR_POWER,
        OutputData(type=OutputType.POWER, unit="kW", values=values, state_last=state_last),
        forecast_times=_TIMES[:times],
        currency_sym="$",
    )

    assert output.state == state
    expected = None if forecast is None else [{"time": _TIMES[i], "value": v} for i, v in enumerate(forecast)]
    assert output.forecast == expected
    assert output.interpolation_mode == interpolation_mode


@pytest.mark.parametrize("value_count", [2, 5], ids=["too-few", "too-many"])
def test_build_coordinator_output_rejects_values_that_do_not_fit_the_forecast_times(value_count: int) -> None:
    """Values that are neither interval nor boundary values fail instead of being truncated."""
    with pytest.raises(ValueError, match=f"has {value_count} values for 4 forecast times"):
        build_coordinator_output(
            SOLAR_POWER,
            OutputData(type=OutputType.POWER, unit="kW", values=tuple(float(v) for v in range(value_count))),
            forecast_times=_TIMES[:4],
            currency_sym="$",
        )


@pytest.mark.parametrize(
    ("output_data", "currency", "unit", "entity_category"),
    [
        pytest.param(
            OutputData(type=OutputType.SHADOW_PRICE, unit="$/kWh", values=(0.05,), diagnostic=True),
            "£",
            "£/kWh",
            EntityCategory.DIAGNOSTIC,
            id="diagnostic_price",
        ),
        pytest.param(OutputData(type=OutputType.COST, unit="$", values=(42.0,)), "€", "€", None, id="cost"),
        pytest.param(OutputData(type=OutputType.POWER, unit="kW", values=(1.0,)), "€", "kW", None, id="power"),
    ],
)
def test_build_coordinator_output_unit_and_category(
    output_data: OutputData, currency: str, unit: str, entity_category: EntityCategory | None
) -> None:
    """Monetary units show the detected currency, and diagnostic outputs make diagnostic entities."""
    output = build_coordinator_output(SOLAR_POWER, output_data, forecast_times=None, currency_sym=currency)

    assert output.unit == unit
    assert output.entity_category == entity_category


@pytest.mark.parametrize("direction", ["+", "-", None], ids=["reserve", "headroom", "none"])
def test_build_coordinator_output_carries_state_of_charge_direction(direction: Literal["+", "-"] | None) -> None:
    """The flow a state of charge line holds the batteries ready for carries through to the coordinator output."""
    output_data = OutputData(type=OutputType.STATE_OF_CHARGE, unit="%", values=(0.2, 0.3), direction=direction)

    output = build_coordinator_output(SOLAR_POWER, output_data, forecast_times=_TIMES[:2], currency_sym="$")

    assert output.direction == direction


def test_forecast_datetimes_are_in_home_assistant_time_zone() -> None:
    """Horizon timestamps convert to aware datetimes in the configured time zone."""
    base_time = datetime(2024, 6, 1, tzinfo=UTC)

    times = forecast_datetimes([base_time.timestamp(), (base_time + timedelta(minutes=30)).timestamp()])

    local_tz = dt_util.get_default_time_zone()
    assert times == (base_time.astimezone(local_tz), (base_time + timedelta(minutes=30)).astimezone(local_tz))
    assert [time.tzinfo for time in times or ()] == [local_tz, local_tz]


def test_forecast_datetimes_out_of_range_returns_none() -> None:
    """A timestamp datetime cannot represent leaves the outputs without forecasts."""
    assert forecast_datetimes([0.0, 4e11]) is None


@pytest.mark.parametrize(
    ("units", "fallback", "expected"),
    [
        pytest.param(("£/kWh",), None, "£", id="pounds"),
        pytest.param(("€/MWh",), None, "€", id="euros_per_mwh"),
        pytest.param(("$/kWh",), None, "$", id="dollars"),
        pytest.param(("A$/kWh",), None, "A$", id="australian_dollars"),
        pytest.param(("EUR/kWh",), None, "€", id="currency_code"),
        pytest.param(("kW", "kWh"), None, "$", id="no_price_entity"),
        pytest.param((), None, "$", id="nothing"),
        pytest.param((), "EUR", "€", id="configured_currency"),
        pytest.param(("kW", "£/kWh", "€/kWh"), None, "£", id="first_price_entity"),
        pytest.param(("p/kWh",), None, "£", id="pence"),
        pytest.param(("ct/kWh",), None, "€", id="euro_cents"),
        pytest.param(("c/kWh",), "EUR", "€", id="cents_of_configured_currency"),
        pytest.param(("c/kWh", "£/kWh"), "EUR", "£", id="cents_then_pounds"),
    ],
)
def test_detect_currency_symbol(units: tuple[str, ...], fallback: str | None, expected: str) -> None:
    """The symbol comes from the first price unit that names a currency, then the configured currency, then $."""
    states = {f"sensor.s{index}": source_state(unit) for index, unit in enumerate(units)}
    assert detect_currency_symbol(states, fallback_currency=fallback) == expected


@pytest.mark.parametrize(
    ("units", "expected"),
    [
        pytest.param(("$/kWh", "$/MWh"), {"$": ["sensor.s0", "sensor.s1"]}, id="same_currency"),
        pytest.param(("EUR/kWh", "€/kWh"), {"€": ["sensor.s0", "sensor.s1"]}, id="code_and_symbol"),
        pytest.param(("€/kWh", "c/kWh", "¢/kWh"), {"€": ["sensor.s0"]}, id="cents_of_any_currency"),
        pytest.param(("€/kWh", "ct/kWh"), {"€": ["sensor.s0", "sensor.s1"]}, id="euro_cents"),
        pytest.param(("p/kWh", "€/kWh"), {"£": ["sensor.s0"], "€": ["sensor.s1"]}, id="pence_and_euros"),
        pytest.param(("kW", "£/kWh"), {"£": ["sensor.s1"]}, id="non_price_unit"),
    ],
)
def test_price_currency_sources(units: tuple[str, ...], expected: dict[str, list[str]]) -> None:
    """Price sources group by currency, with codes joining their symbol and plain cents left out."""
    states = {f"sensor.s{i}": source_state(unit) for i, unit in enumerate(units)}

    assert price_currency_sources(states) == expected


async def test_async_update_data_warns_about_mixed_price_currencies(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Price sources in two currencies raise a repair issue without stopping the optimization."""
    store = MagicMock()
    store.available = True
    store.error = None
    store.captured_source_states = {
        "sensor.import_price": source_state("£/kWh"),
        "sensor.export_price": source_state("€/kWh"),
    }
    mock_runtime_data.input_stores[("Main Grid", (SECTION_PRICING, CONF_PRICE_SOURCE_TARGET))] = store
    issue_id = f"mixed_price_currencies_{mock_hub_entry.entry_id}"

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._network = MagicMock()

    with (
        patch.object(coordinator, "_load_from_input_stores", return_value={}),
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, side_effect=UpdateFailed("solved")),
        pytest.raises(UpdateFailed, match="solved"),
    ):
        await coordinator._async_update_data()

    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

    store.captured_source_states = {"sensor.import_price": source_state("€/kWh")}
    with (
        patch.object(coordinator, "_load_from_input_stores", return_value={}),
        patch.object(hass, "async_add_executor_job", new_callable=AsyncMock, side_effect=UpdateFailed("solved")),
        pytest.raises(UpdateFailed, match="solved"),
    ):
        await coordinator._async_update_data()

    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
