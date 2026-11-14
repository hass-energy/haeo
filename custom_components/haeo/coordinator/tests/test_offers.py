"""Tests for the coordinator's grid offer curves."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import numpy as np
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.coordinator.tests.helpers import network_double
from custom_components.haeo.core.adapters.offer import GridOffer
from custom_components.haeo.core.model import SolverError
from custom_components.haeo.core.model.infeasibility import Relaxation, RowLabel

# A plan of three periods that starts at 10:00 UTC and runs for an hour
PLAN_START = 36000.0
PLAN_TIMESTAMPS = (PLAN_START, PLAN_START + 600.0, PLAN_START + 1800.0, PLAN_START + 3600.0)
# An interval inside the plan
INTERVAL = (PLAN_START + 300.0, PLAN_START + 600.0)


def _planned(hass: HomeAssistant, entry: MockConfigEntry) -> HaeoDataUpdateCoordinator:
    """Return a coordinator holding a plan over three periods."""
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    coordinator._network = network_double()
    coordinator._network.relaxations = ()
    coordinator._plan_timestamps = PLAN_TIMESTAMPS
    return coordinator


async def test_grid_offers_trace_the_grid_over_intervals_from_the_start_of_the_plan(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """The grid is traced over each interval in the order given, timed from the start of the plan."""
    coordinator = _planned(hass, mock_hub_entry)
    offer = GridOffer(import_price=0.3, export_price=0.05, power=1.0, emissions_intensity=None, steps=())
    intervals = [INTERVAL, (PLAN_START, PLAN_START + 3600.0), (PLAN_START + 700.0, PLAN_START + 2000.0)]

    with patch("custom_components.haeo.coordinator.coordinator.grid_offers", return_value=[offer] * 3) as traced:
        offers = await coordinator.async_grid_offers("Test Grid", intervals=intervals, min_price=-1.0, max_price=2.0)

    assert offers == [offer] * 3
    traced.assert_called_once_with(
        coordinator.network,
        "Test Grid",
        intervals=[(300.0, 600.0), (0.0, 3600.0), (700.0, 2000.0)],
        min_price=-1.0,
        max_price=2.0,
        emissions_intensity=None,
    )


@pytest.mark.parametrize(
    "interval",
    [
        pytest.param((PLAN_START - 300.0, PLAN_START + 300.0), id="starts_before_the_plan"),
        pytest.param((PLAN_START + 3300.0, PLAN_START + 3900.0), id="ends_after_the_plan"),
        pytest.param((PLAN_START + 600.0, PLAN_START + 600.0), id="empty"),
        pytest.param((PLAN_START + 600.0, PLAN_START + 300.0), id="ends_before_it_starts"),
    ],
)
async def test_grid_offers_need_each_interval_inside_the_plan(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
    interval: tuple[float, float],
) -> None:
    """An interval that is empty or reaches outside the plan is reported with the time the plan covers."""
    await hass.config.async_set_time_zone("UTC")
    coordinator = _planned(hass, mock_hub_entry)

    with pytest.raises(HomeAssistantError) as error:
        await coordinator.async_grid_offers("Test Grid", intervals=[INTERVAL, interval], min_price=-1.0, max_price=2.0)

    assert error.value.translation_key == "offer_interval_outside_plan"
    assert error.value.translation_placeholders is not None
    assert error.value.translation_placeholders["plan_start"] == "1970-01-01T10:00:00+00:00"
    assert error.value.translation_placeholders["plan_end"] == "1970-01-01T11:00:00+00:00"


async def test_grid_offers_report_a_solver_failure(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """A solve that ends without a plan while tracing is reported with the solver's status."""
    coordinator = _planned(hass, mock_hub_entry)

    with (
        patch("custom_components.haeo.coordinator.coordinator.grid_offers", side_effect=SolverError("Time limit")),
        pytest.raises(HomeAssistantError) as error,
    ):
        await coordinator.async_grid_offers("Test Grid", intervals=[INTERVAL], min_price=-1.0, max_price=2.0)

    assert error.value.translation_key == "optimization_solver_failed"
    assert error.value.translation_placeholders == {"status": "Time limit"}


async def test_grid_offers_hand_on_an_optimization_requested_while_tracing(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """A request made while the curves hold the optimization lock is signaled once they are done."""
    coordinator = _planned(hass, mock_hub_entry)

    with (
        patch("custom_components.haeo.coordinator.coordinator.grid_offers", return_value=[]),
        patch.object(coordinator, "signal_optimization_stale") as signaled,
    ):
        await coordinator.async_grid_offers("Test Grid", intervals=[INTERVAL], min_price=-1.0, max_price=2.0)
        signaled.assert_not_called()

        with patch(
            "custom_components.haeo.coordinator.coordinator.load_emissions_intensity",
            side_effect=lambda *_args: coordinator._request_optimization(),
        ):
            await coordinator.async_grid_offers(
                "Test Grid", intervals=[INTERVAL], min_price=-1.0, max_price=2.0, emissions_intensity="sensor.any"
            )
        signaled.assert_called_once_with()


async def test_grid_offers_need_a_plan(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Before an optimization finds a plan there is nothing to offer from."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with pytest.raises(HomeAssistantError) as error:
        await coordinator.async_grid_offers("Test Grid", intervals=[INTERVAL], min_price=-1.0, max_price=2.0)

    assert error.value.translation_key == "offer_no_plan"


async def test_grid_offers_need_the_latest_optimization_to_succeed(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """A failed optimization leaves the network without the plan the timestamps describe."""
    coordinator = _planned(hass, mock_hub_entry)
    coordinator.last_update_success = False

    with pytest.raises(HomeAssistantError) as error:
        await coordinator.async_grid_offers("Test Grid", intervals=[INTERVAL], min_price=-1.0, max_price=2.0)

    assert error.value.translation_key == "offer_no_plan"


async def test_grid_offers_refuse_a_relaxed_plan(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """A relaxed plan's model has its bounds back, so it has no curve to trace."""
    coordinator = _planned(hass, mock_hub_entry)
    coordinator.network.relaxations = (Relaxation(RowLabel("Battery", "soc", 0), 1.0),)

    with pytest.raises(HomeAssistantError) as error:
        await coordinator.async_grid_offers("Test Grid", intervals=[INTERVAL], min_price=-1.0, max_price=2.0)

    assert error.value.translation_key == "offer_relaxed_plan"


async def test_grid_offers_read_the_emissions_intensity_over_the_plans_periods(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """An emissions intensity sensor is read for each period of the plan, in kg/kWh."""
    hass.states.async_set("sensor.intensity", "600", {"unit_of_measurement": "gCO2eq/kWh"})
    coordinator = _planned(hass, mock_hub_entry)

    with patch("custom_components.haeo.coordinator.coordinator.grid_offers", return_value=[]) as traced:
        await coordinator.async_grid_offers(
            "Test Grid", intervals=[INTERVAL], min_price=-1.0, max_price=2.0, emissions_intensity="sensor.intensity"
        )

    np.testing.assert_allclose(traced.call_args.kwargs["emissions_intensity"], [0.6, 0.6, 0.6])


async def test_grid_offers_report_an_unreadable_emissions_intensity(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """A sensor that does not give an emissions intensity is reported by name."""
    hass.states.async_set("sensor.intensity", "40", {"unit_of_measurement": "%"})
    coordinator = _planned(hass, mock_hub_entry)

    with pytest.raises(HomeAssistantError) as error:
        await coordinator.async_grid_offers(
            "Test Grid", intervals=[INTERVAL], min_price=-1.0, max_price=2.0, emissions_intensity="sensor.intensity"
        )

    assert error.value.translation_key == "emissions_intensity_unit"
    assert error.value.translation_placeholders == {"entity_id": "sensor.intensity", "unit": "%"}
