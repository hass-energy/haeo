"""Tests for how the coordinator reports failed and relaxed optimizations."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from freezegun import freeze_time
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import DOMAIN
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.coordinator.coordinator import FAILURE_SECONDS_BEFORE_REPAIR_ISSUE, ReportedUpdateFailed
from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.model import SolverError
from custom_components.haeo.core.model.infeasibility import InfeasibleError, Relaxation, RowLabel
from custom_components.haeo.core.schema.elements.battery import CONF_MAX_POWER_SOURCE_TARGET
from custom_components.haeo.core.schema.elements.grid import CONF_PRICE_SOURCE_TARGET
from custom_components.haeo.core.schema.sections import SECTION_POWER_LIMITS, SECTION_PRICING
from custom_components.haeo.repairs import create_optimization_infeasible_issue, create_optimization_relaxed_issue

from .helpers import EARLIER_DIAGNOSTICS, EARLIER_ISSUE, saved_diagnostics


async def test_failures_raise_one_repair_issue_after_failing_for_a_while(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Failures show as failed at once, raise one repair issue after failing for a while, and success clears it."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    issue_id = f"optimization_failure_{mock_hub_entry.entry_id}"
    assert coordinator.optimization_status == "pending"
    errors = [ValueError("Infeasible"), ValueError("Infeasible"), ValueError("Infeasible"), ValueError("Unbounded")]

    with (
        freeze_time("2025-01-01 12:00:00") as frozen,
        patch.object(coordinator, "_async_update_data", AsyncMock(side_effect=errors)),
    ):
        await coordinator.async_refresh()
        frozen.tick(FAILURE_SECONDS_BEFORE_REPAIR_ISSUE - 1)
        await coordinator.async_refresh()
        assert coordinator.optimization_status == "failed"
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

        frozen.tick(1)
        await coordinator.async_refresh()
        frozen.tick(60)
        await coordinator.async_refresh()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders == {"error_message": "ValueError: Infeasible"}
    assert coordinator.optimization_error == "ValueError: Unbounded"

    with patch.object(coordinator, "_async_update_data", AsyncMock(return_value=Mock())):
        await coordinator.async_refresh()
    assert coordinator.optimization_status == "success"
    assert coordinator.optimization_error is None
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def _keep_failing_past_the_repair_delay(coordinator: HaeoDataUpdateCoordinator) -> None:
    """Refresh a failing coordinator until it has failed for longer than a repair issue waits."""
    with (
        freeze_time("2025-01-01 12:00:00") as frozen,
        patch.object(coordinator, "_load_from_input_stores", return_value={}),
    ):
        await coordinator.async_refresh()
        frozen.tick(FAILURE_SECONDS_BEFORE_REPAIR_ISSUE)
        await coordinator.async_refresh()
    assert coordinator.optimization_status == "failed"


@pytest.mark.parametrize(
    ("diagnostics_saved", "general_issue_raised"),
    [
        pytest.param(True, False, id="own_issue"),
        pytest.param(False, True, id="diagnostics_not_saved"),
    ],
)
@pytest.mark.usefixtures("mock_grid_subentry", "mock_runtime_data")
async def test_infeasible_plans_raise_the_general_issue_only_without_their_own(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    tmp_path: Path,
    diagnostics_saved: bool,
    general_issue_raised: bool,
) -> None:
    """Infeasible plans that keep failing are reported by their own issue, or by the general one when it is missing."""
    hass.config.config_dir = str(tmp_path)
    if not diagnostics_saved:
        # A file where the diagnostics folder belongs makes writing it fail
        (tmp_path / "haeo").mkdir()
        (tmp_path / "haeo" / "diagnostics").write_text("")
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    network = MagicMock()
    coordinator._network = network
    network.optimize.side_effect = InfeasibleError((RowLabel("Test Grid:import", "power_limit", 1),))

    await _keep_failing_past_the_repair_delay(coordinator)

    issues = ir.async_get(hass)
    entry_id = mock_hub_entry.entry_id
    assert (issues.async_get_issue(DOMAIN, f"optimization_infeasible_{entry_id}") is not None) == diagnostics_saved
    assert (issues.async_get_issue(DOMAIN, f"optimization_failure_{entry_id}") is not None) == general_issue_raised


async def test_unavailable_inputs_raise_only_their_own_issue(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """An input that stays without a reading is reported by its own issue, not the general one."""
    unavailable_store = MagicMock()
    unavailable_store.available = False
    unavailable_store.error = None
    unavailable_store.source_entity_ids = ["sensor.price"]
    unavailable_store.unavailable_sources = ("sensor.price",)
    unavailable_store.captured_source_states = {}
    mock_runtime_data.input_stores[("Grid", (SECTION_PRICING, CONF_PRICE_SOURCE_TARGET))] = unavailable_store
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._network = MagicMock()

    await _keep_failing_past_the_repair_delay(coordinator)

    issues = ir.async_get(hass)
    entry_id = mock_hub_entry.entry_id
    field = f"{SECTION_PRICING}.{CONF_PRICE_SOURCE_TARGET}"
    assert issues.async_get_issue(DOMAIN, f"unavailable_input_{entry_id}_Grid_{field}") is not None
    assert issues.async_get_issue(DOMAIN, f"optimization_failure_{entry_id}") is None


async def test_repeated_failures_notify_listeners(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Every failure notifies listeners, so the reported error stays current."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    listener = Mock()
    coordinator.async_add_listener(listener)

    with patch.object(coordinator, "_async_update_data", AsyncMock(side_effect=ValueError("Infeasible"))):
        for _ in range(3):
            await coordinator.async_refresh()

    assert listener.call_count == 3


async def test_failures_of_a_new_kind_wait_before_raising_the_general_issue(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Time spent failing with a cause that has its own issue does not count toward the general one."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    errors = [ReportedUpdateFailed("Input unavailable"), ReportedUpdateFailed("Input unavailable"), ValueError("x")]

    with (
        freeze_time("2025-01-01 12:00:00") as frozen,
        patch.object(coordinator, "_async_update_data", AsyncMock(side_effect=errors)),
    ):
        await coordinator.async_refresh()
        frozen.tick(FAILURE_SECONDS_BEFORE_REPAIR_ISSUE)
        await coordinator.async_refresh()
        frozen.tick(1)
        await coordinator.async_refresh()

    assert ir.async_get(hass).async_get_issue(DOMAIN, f"optimization_failure_{mock_hub_entry.entry_id}") is None


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(
            UpdateFailed("Element 'Grid' has unavailable inputs"),
            "Element 'Grid' has unavailable inputs",
            id="ha_error",
        ),
        pytest.param(KeyError("battery"), "KeyError: 'battery'", id="other_error"),
        pytest.param(TimeoutError(), "TimeoutError", id="no_message"),
    ],
)
async def test_optimization_error_message(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
    error: Exception,
    expected: str,
) -> None:
    """Home Assistant errors read as they are, and other errors are prefixed with their type."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)

    with patch.object(coordinator, "_async_update_data", AsyncMock(side_effect=error)):
        await coordinator.async_refresh()

    assert coordinator.optimization_error == expected


@pytest.mark.parametrize(
    ("conflicts", "translation_key", "placeholders"),
    [
        pytest.param(
            (
                RowLabel("Switchboard", "element_power_balance", 2, balance=True),
                RowLabel("Test Grid:import", "power_limit_power_limit", 1),
                RowLabel("Test Grid:import", "power_limit_power_limit", 2),
            ),
            "optimization_infeasible",
            {"elements": "Switchboard, Test Grid", "minutes": "17"},
            id="conflicts",
        ),
        pytest.param((), "optimization_infeasible_unexplained", {}, id="no_conflicts"),
    ],
)
@pytest.mark.usefixtures("mock_grid_subentry")
async def test_async_update_data_reports_an_infeasible_plan(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
    conflicts: tuple[RowLabel, ...],
    translation_key: str,
    placeholders: dict[str, str],
    tmp_path: Path,
) -> None:
    """An infeasible plan fails the update with a repair issue naming the elements and how far into the plan."""
    hass.config.config_dir = str(tmp_path)
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    network = MagicMock()
    coordinator._network = network
    network.optimize.side_effect = InfeasibleError(conflicts)
    create_optimization_relaxed_issue(hass, mock_hub_entry.entry_id, EARLIER_ISSUE, EARLIER_DIAGNOSTICS)

    with (
        patch.object(coordinator, "_load_from_input_stores", return_value={}),
        pytest.raises(UpdateFailed) as error,
    ):
        await coordinator._async_update_data()

    assert error.value.translation_key == translation_key
    assert error.value.translation_placeholders == placeholders
    issues = ir.async_get(hass)
    issue = issues.async_get_issue(DOMAIN, f"optimization_infeasible_{mock_hub_entry.entry_id}")
    assert issue is not None
    assert issue.translation_key == translation_key
    planned_at = f"{dt_util.as_local(dt_util.utc_from_timestamp(1000.0)):%Y-%m-%d %H:%M}"
    assert issue.translation_placeholders is not None
    path = issue.translation_placeholders["diagnostics"]
    assert issue.translation_placeholders == {**placeholders, "planned_at": planned_at, "diagnostics": path}
    diagnostics = saved_diagnostics(hass, path, "infeasible")
    assert diagnostics["data"]["failure"] == {"conflicts": [str(row) for row in conflicts]}
    assert {"config", "environment", "inputs"} <= diagnostics["data"].keys()
    # An earlier relaxation stays for the user to resolve
    assert issues.async_get_issue(DOMAIN, f"optimization_relaxed_{mock_hub_entry.entry_id}") is not None


@pytest.mark.parametrize("cause", ["unwritable_folder", "collection_error"])
@pytest.mark.usefixtures("mock_grid_subentry")
async def test_async_update_data_reports_an_infeasible_plan_whose_diagnostics_cannot_be_saved(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    cause: str,
) -> None:
    """Diagnostics that cannot be saved leave the issue for the next plan, and still report the failure."""
    # HAEO's loggers write to the console only, so let this one reach caplog
    monkeypatch.setattr(logging.getLogger("custom_components.haeo"), "propagate", True)
    hass.config.config_dir = str(tmp_path)
    if cause == "unwritable_folder":
        # A file where the diagnostics folder belongs makes writing it fail
        (tmp_path / "haeo").mkdir()
        (tmp_path / "haeo" / "diagnostics").write_text("")
    else:
        monkeypatch.setattr(
            "custom_components.haeo.diagnostics.diagnostics_from_context", AsyncMock(side_effect=KeyError("Grid"))
        )
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    network = MagicMock()
    coordinator._network = network
    network.optimize.side_effect = InfeasibleError((RowLabel("Test Grid:import", "power_limit", 1),))

    with (
        patch.object(coordinator, "_load_from_input_stores", return_value={}),
        pytest.raises(UpdateFailed) as error,
    ):
        await coordinator._async_update_data()

    assert error.value.translation_key == "optimization_infeasible"
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"optimization_infeasible_{mock_hub_entry.entry_id}") is None
    assert "Could not save the infeasible plan's diagnostics" in caplog.text


@pytest.mark.usefixtures("mock_grid_subentry", "mock_runtime_data")
async def test_async_update_data_reports_a_solver_failure(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """A solve that stops for a reason other than infeasibility fails the update with the solver status."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    network = MagicMock()
    coordinator._network = network
    network.optimize.side_effect = SolverError("Unbounded")

    with (
        patch.object(coordinator, "_load_from_input_stores", return_value={}),
        pytest.raises(UpdateFailed) as error,
    ):
        await coordinator._async_update_data()

    assert error.value.translation_key == "optimization_solver_failed"
    assert error.value.translation_placeholders == {"status": "Unbounded"}


async def test_async_update_data_keeps_an_unresolved_infeasible_issue_and_its_diagnostics(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
    tmp_path: Path,
) -> None:
    """Another impossible plan leaves the issue the user has not resolved, and saves no more diagnostics."""
    hass.config.config_dir = str(tmp_path)
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    network = MagicMock()
    coordinator._network = network
    network.optimize.side_effect = InfeasibleError((RowLabel("Switchboard", "element_power_balance", 0),))
    create_optimization_infeasible_issue(
        hass, mock_hub_entry.entry_id, "optimization_infeasible", EARLIER_ISSUE, EARLIER_DIAGNOSTICS
    )

    with (
        patch.object(coordinator, "_load_from_input_stores", return_value={}),
        pytest.raises(UpdateFailed),
    ):
        await coordinator._async_update_data()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"optimization_infeasible_{mock_hub_entry.entry_id}")
    assert issue is not None
    assert issue.translation_placeholders == {**EARLIER_ISSUE, "diagnostics": EARLIER_DIAGNOSTICS}
    assert not Path(hass.config.path("haeo", "diagnostics")).exists()


async def test_every_relaxed_plan_is_logged(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A relaxed plan logs a warning even while an earlier relaxation's issue is still raised."""
    # HAEO's loggers write to the console only, so let this one reach caplog
    monkeypatch.setattr(logging.getLogger("custom_components.haeo"), "propagate", True)
    create_optimization_relaxed_issue(hass, mock_hub_entry.entry_id, EARLIER_ISSUE, EARLIER_DIAGNOSTICS)
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    network = MagicMock()
    coordinator._network = network
    network.optimize.return_value = 1.0
    network.elements = {}
    network.relaxations = (Relaxation(RowLabel("Switchboard", "element_power_balance", 0), 0.1),)

    with patch.object(coordinator, "_load_from_input_stores", return_value={}):
        await coordinator._async_update_data()

    assert "The plan relaxed constraints it cannot meet" in caplog.text


async def test_async_update_data_raises_when_inputs_unavailable(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Optimization is skipped with an error and a repair issue naming the sensor with no reading."""
    unavailable_store = MagicMock()
    unavailable_store.available = False
    unavailable_store.error = None
    unavailable_store.source_entity_ids = ["sensor.price_a", "sensor.price_b"]
    unavailable_store.unavailable_sources = ("sensor.price_b",)
    unavailable_store.captured_source_states = {}
    mock_runtime_data.input_stores[("Unavailable Grid", (SECTION_PRICING, CONF_PRICE_SOURCE_TARGET))] = (
        unavailable_store
    )

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._network = MagicMock()

    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()

    placeholders = {
        "element": "Unavailable Grid",
        "field": f"{SECTION_PRICING}.{CONF_PRICE_SOURCE_TARGET}",
        "entities": "sensor.price_b",
    }
    assert exc_info.value.translation_key == "input_unavailable"
    assert exc_info.value.translation_placeholders == placeholders
    issue = ir.async_get(hass).async_get_issue(
        DOMAIN,
        f"unavailable_input_{mock_hub_entry.entry_id}_Unavailable Grid_{SECTION_PRICING}.{CONF_PRICE_SOURCE_TARGET}",
    )
    assert issue is not None
    assert issue.translation_key == "unavailable_input"
    assert issue.translation_placeholders == placeholders


async def test_async_update_data_raises_translated_input_error(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """A store that rejected its value fails the update with the error's translation and the input's context."""
    rejected_store = MagicMock()
    rejected_store.available = False
    rejected_store.error = InputError(
        translation_key="negative_input_value", translation_placeholders={"value": "-4.5"}
    )
    rejected_store.source_entity_ids = ["sensor.import_limit"]
    rejected_store.captured_source_states = {}
    mock_runtime_data.input_stores[("Main Grid", (SECTION_POWER_LIMITS, CONF_MAX_POWER_SOURCE_TARGET))] = rejected_store

    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    coordinator._network = MagicMock()

    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()

    assert exc_info.value.translation_key == "negative_input_value"
    assert exc_info.value.translation_placeholders == {
        "element": "Main Grid",
        "field": f"{SECTION_POWER_LIMITS}.{CONF_MAX_POWER_SOURCE_TARGET}",
        "entities": "sensor.import_limit",
        "value": "-4.5",
    }
    assert not [issue_id for _, issue_id in ir.async_get(hass).issues if issue_id.startswith("unavailable_input_")]


async def test_a_cause_with_its_own_issue_dismisses_the_general_one(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    mock_runtime_data: HaeoRuntimeData,
) -> None:
    """Once failures switch to a cause with its own issue, the general issue goes, so the user sees one."""
    coordinator = HaeoDataUpdateCoordinator(hass, mock_hub_entry)
    issue_id = f"optimization_failure_{mock_hub_entry.entry_id}"
    errors = [ValueError("x"), ValueError("x"), ReportedUpdateFailed("Input unavailable")]

    with (
        freeze_time("2025-01-01 12:00:00") as frozen,
        patch.object(coordinator, "_async_update_data", AsyncMock(side_effect=errors)),
    ):
        await coordinator.async_refresh()
        frozen.tick(FAILURE_SECONDS_BEFORE_REPAIR_ISSUE)
        await coordinator.async_refresh()
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
        frozen.tick(1)
        await coordinator.async_refresh()

    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
