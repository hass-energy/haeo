"""Tests for the plugin that checks the strings shown during each test."""

import pytest

from custom_components.haeo.translations.tests.runtime_checks import TranslationChecker, TranslationPath


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
