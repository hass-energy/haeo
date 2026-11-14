"""Tests for the coordinator's grid offer curves."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import numpy as np
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.coordinator.tests.helpers import network_double
from custom_components.haeo.core.adapters.offer import GridOffer
from custom_components.haeo.core.model.infeasibility import Relaxation, RowLabel

# Two 30 minute intervals, the first split into periods of 10 and 20 minutes
PLAN_TIMESTAMPS = (0.0, 600.0, 1800.0, 3600.0)


def _planned(hass: HomeAssistant, entry: MockConfigEntry) -> HaeoDataUpdateCoordinator:
    """Return a coordinator holding a plan over three periods."""
    coordinator = HaeoDataUpdateCoordinator(hass, entry)
    coordinator._network = network_double()
    coordinator._network.relaxations = ()
    coordinator._plan_timestamps = PLAN_TIMESTAMPS
    return coordinator


@pytest.mark.parametrize(
    ("start", "end", "interval", "windows"),
    [
        pytest.param(0.0, None, 1800.0, [[0, 1]], id="next_interval"),
        pytest.param(700.0, None, 1800.0, [[2]], id="start_inside_an_interval"),
        pytest.param(-5000.0, None, 1800.0, [[0, 1]], id="start_before_the_plan"),
        pytest.param(0.0, 3600.0, 1800.0, [[0, 1], [2]], id="every_interval_before_the_end"),
        pytest.param(0.0, 1800.0, 1800.0, [[0, 1]], id="end_on_an_interval_start"),
        pytest.param(0.0, 3600.0, 600.0, [[0], [1], [2]], id="shorter_than_periods"),
        pytest.param(0.0, 3600.0, 3600.0, [[0, 1, 2]], id="hour"),
        pytest.param(0.0, None, 7200.0, [], id="plan_ends_inside_the_interval"),
        pytest.param(3600.0, None, 1800.0, [], id="start_after_the_plan"),
    ],
)
async def test_grid_offers_trace_each_grid_over_whole_intervals_from_the_start(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_grid_subentry: ConfigSubentry,
    mock_battery_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
    start: float,
    end: float | None,
    interval: float,
    windows: list[list[int]],
) -> None:
    """Every grid is traced over the intervals the plan covers whole, the first one alone without an end."""
    coordinator = _planned(hass, mock_hub_entry)
    offer = GridOffer(periods=(0,), import_price=0.3, export_price=0.05, power=1.0, emissions_intensity=None, steps=())

    with patch("custom_components.haeo.coordinator.coordinator.grid_offers", return_value=[offer]) as traced:
        timestamps, offers = await coordinator.async_grid_offers(
            start=start, end=end, interval=interval, min_price=-1.0, max_price=2.0
        )

    assert timestamps == PLAN_TIMESTAMPS
    assert offers == {"Test Grid": [offer]}
    traced.assert_called_once_with(
        coordinator.network,
        "Test Grid",
        windows=windows,
        min_price=-1.0,
        max_price=2.0,
        emissions_intensity=None,
    )


async def test_grid_offers_skip_the_interval_the_plan_starts_inside(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """The rest of an interval already under way is not offered, however early the start."""
    coordinator = _planned(hass, mock_hub_entry)
    coordinator._plan_timestamps = PLAN_TIMESTAMPS[1:]

    with patch("custom_components.haeo.coordinator.coordinator.grid_offers", return_value=[]) as traced:
        await coordinator.async_grid_offers(start=0.0, end=None, interval=1800.0, min_price=-1.0, max_price=2.0)

    assert traced.call_args.kwargs["windows"] == [[1]]


async def test_grid_offers_need_a_plan(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Before an optimization finds a plan there is nothing to offer from."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with pytest.raises(HomeAssistantError) as error:
        await coordinator.async_grid_offers(start=0.0, end=1.0, interval=1800.0, min_price=-1.0, max_price=2.0)

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
        await coordinator.async_grid_offers(start=0.0, end=1.0, interval=1800.0, min_price=-1.0, max_price=2.0)

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
        await coordinator.async_grid_offers(start=0.0, end=1.0, interval=1800.0, min_price=-1.0, max_price=2.0)

    assert error.value.translation_key == "offer_relaxed_plan"


async def test_grid_offers_read_the_emissions_intensity_over_the_plans_periods(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_grid_subentry: ConfigSubentry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """An emissions intensity sensor is read for each period of the plan, in kg/kWh."""
    hass.states.async_set("sensor.intensity", "600", {"unit_of_measurement": "gCO2eq/kWh"})
    coordinator = _planned(hass, mock_hub_entry)

    with patch("custom_components.haeo.coordinator.coordinator.grid_offers", return_value=[]) as traced:
        await coordinator.async_grid_offers(
            start=0.0, end=1.0, interval=1800.0, min_price=-1.0, max_price=2.0, emissions_intensity="sensor.intensity"
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
            start=0.0, end=1.0, interval=1800.0, min_price=-1.0, max_price=2.0, emissions_intensity="sensor.intensity"
        )

    assert error.value.translation_key == "emissions_intensity_unit"
    assert error.value.translation_placeholders == {"entity_id": "sensor.intensity", "unit": "%"}
