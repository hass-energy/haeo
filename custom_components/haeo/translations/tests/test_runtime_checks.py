"""Tests for the plugin that checks the strings shown during each test."""

from collections.abc import Mapping

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.selector import ChooseSelector, ChooseSelectorConfig, SelectSelector, SelectSelectorConfig
from homeassistant.util import dt as dt_util
import pytest
import voluptuous as vol

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.repairs import async_create_fix_flow
from custom_components.haeo.translations.tests import runtime_checks
from custom_components.haeo.translations.tests.runtime_checks import (
    TranslationChecker,
    TranslationPath,
    flow_strings,
    selector_translation_paths,
)


@pytest.fixture
def fake_translations(monkeypatch: pytest.MonkeyPatch) -> Mapping[str, object]:
    """Replace en.json with a small set of strings."""
    translations: Mapping[str, object] = {
        "config": {"step": {"user": {"data": {"limit": "Limit for {element}"}}}},
        "issues": {
            "label_only": {"title": "Title"},
            "confirmed": {
                "title": "Title",
                "fix_flow": {"step": {"confirm": {"title": "Confirm", "description": "Fix {element}"}}},
            },
        },
    }
    monkeypatch.setattr(runtime_checks, "load_translations", lambda: translations)
    return translations


@pytest.mark.parametrize(
    ("path", "placeholders", "problems"),
    [
        pytest.param(
            ("issues", "unavailable_input", "title"), {"element": "Battery", "field": "Capacity"}, [], id="ok"
        ),
        pytest.param(
            ("issues", "no_such_issue", "title"), None, ["Missing translation issues.no_such_issue.title"], id="missing"
        ),
        pytest.param(
            ("issues", "unavailable_input", "title"),
            {"element": "Battery"},
            ["issues.unavailable_input.title uses placeholder {field}, which is not supplied"],
            id="placeholder",
        ),
    ],
)
def test_require_reports_missing_strings_and_placeholders(
    path: TranslationPath, placeholders: dict[str, str] | None, problems: list[str]
) -> None:
    """A required string must exist and be given every placeholder it uses."""
    checker = TranslationChecker()

    checker.require(path, placeholders)

    assert checker.problems == problems


def test_choose_selector_paths_include_serialized_nested_selectors() -> None:
    """Option labels of a selector nested in a choose selector in serialized form are checked."""
    nested = SelectSelector(SelectSelectorConfig(options=["low"], translation_key="nested"))
    choose = ChooseSelector(
        ChooseSelectorConfig(choices={"pick": {"selector": nested.serialize()["selector"]}}, translation_key="outer")
    )

    assert set(selector_translation_paths(choose)) == {
        ("selector", "outer", "choices", "pick"),
        ("selector", "nested", "options", "low"),
    }


@pytest.mark.usefixtures("fake_translations")
@pytest.mark.parametrize(
    ("placeholders", "problems"),
    [
        pytest.param({"element": "Battery"}, [], id="supplied"),
        pytest.param(
            {},
            ["config.step.user.data.limit uses placeholder {element}, which is not supplied"],
            id="not_supplied",
        ),
    ],
)
def test_form_labels_use_the_step_placeholders(placeholders: dict[str, str], problems: list[str]) -> None:
    """Field labels are formatted with the placeholders the step supplies."""
    checker = TranslationChecker()
    result = FlowResult(
        type=FlowResultType.FORM,
        flow_id="flow",
        handler=DOMAIN,
        step_id="user",
        data_schema=vol.Schema({vol.Required("limit"): str}),
        description_placeholders=placeholders,
    )

    checker.check_form(("config",), placeholders, result)

    assert checker.problems == problems


async def test_repair_flow_of_a_deleted_issue_has_no_strings(hass: HomeAssistant) -> None:
    """A repair flow whose issue is already gone is skipped rather than raising."""
    flow = RepairsFlow()
    flow.hass = hass
    flow.handler = DOMAIN
    flow.issue_id = "already_deleted"

    assert flow_strings(flow, None) is None


def _issue(translation_key: str, *, is_fixable: bool) -> ir.IssueEntry:
    return ir.IssueEntry(
        active=True,
        breaks_in_ha_version=None,
        created=dt_util.utcnow(),
        data=None,
        dismissed_version=None,
        domain=DOMAIN,
        is_fixable=is_fixable,
        is_persistent=True,
        issue_domain=None,
        issue_id=translation_key,
        learn_more_url=None,
        severity=ir.IssueSeverity.WARNING,
        translation_key=translation_key,
        translation_placeholders={"element": "Battery"},
    )


@pytest.mark.usefixtures("fake_translations")
@pytest.mark.parametrize(
    ("translation_key", "problems"),
    [
        pytest.param("confirmed", [], id="confirm_step_translated"),
        pytest.param(
            "label_only",
            [
                "Missing translation issues.label_only.fix_flow.step.confirm.title",
                "Missing translation issues.label_only.fix_flow.step.confirm.description",
            ],
            id="confirm_step_missing",
        ),
    ],
)
def test_fixable_issues_need_their_confirm_step(translation_key: str, problems: list[str]) -> None:
    """A fixable issue is checked for the step its fix flow shows as soon as it is created."""
    checker = TranslationChecker()

    checker.check_issue(_issue(translation_key, is_fixable=True))

    assert checker.problems == problems


async def test_fixable_issues_are_fixed_by_a_confirm_flow(hass: HomeAssistant) -> None:
    """The confirm step the checks require is the step the integration's fix flow shows."""
    assert isinstance(await async_create_fix_flow(hass, "issue", None), ConfirmRepairFlow)
