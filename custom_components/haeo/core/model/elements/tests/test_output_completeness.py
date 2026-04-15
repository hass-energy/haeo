"""Test that model element output methods match OUTPUT_NAMES declarations.

This ensures that:
1. Every name in *_OUTPUT_NAMES has a corresponding @output or @constraint(output=True) method
2. Every @output/@constraint(output=True) method has its name in *_OUTPUT_NAMES

This prevents drift between declared outputs and implemented methods.
"""

import pytest

from custom_components.haeo.core.model.elements import ELEMENTS, ElementSpec
from custom_components.haeo.core.model.reactive import OutputMethod, ReactiveConstraint


def get_output_methods(cls: type) -> set[str]:
    """Get all @output/@constraint(output=True) names available on a class (including inherited)."""
    output_names = set()
    for name in dir(cls):
        attr = getattr(cls, name, None)
        if isinstance(attr, OutputMethod):
            output_names.add(attr.output_name)
        elif isinstance(attr, ReactiveConstraint) and attr.output:
            output_names.add(name)
    return output_names


def get_own_output_methods(cls: type) -> set[str]:
    """Get @output/@constraint(output=True) names defined directly on this class (not inherited)."""
    output_names = set()
    for name, attr in cls.__dict__.items():
        if isinstance(attr, OutputMethod):
            output_names.add(attr.output_name)
        elif isinstance(attr, ReactiveConstraint) and attr.output:
            output_names.add(name)
    return output_names


@pytest.mark.parametrize(
    ("element_type", "element_spec"),
    ELEMENTS.items(),
    ids=lambda x: x if isinstance(x, str) else x.factory.__name__,
)
def test_output_methods_match_declarations(element_type: str, element_spec: ElementSpec) -> None:
    """Test that @output methods match output_names in element spec.

    Args:
        element_type: The element type string
        element_spec: The element specification with factory and output_names

    """
    element_class = element_spec.factory
    output_names_constant = element_spec.output_names

    # Get actual output methods from the class (including inherited, for "missing" check)
    all_methods = get_output_methods(element_class)
    # Get only methods defined on this class (for "extra" check)
    own_methods = get_own_output_methods(element_class)

    # Get declared output names from the constant
    declared_names = set(output_names_constant)

    # Missing: declared in output_names but no method exists (including inherited)
    missing_methods = declared_names - all_methods
    # Extra: defined directly on this class but not in output_names
    extra_methods = own_methods - declared_names

    error_parts = []
    if missing_methods:
        error_parts.append(f"Missing @output methods in {element_class.__name__}: {sorted(missing_methods)}")
    if extra_methods:
        error_parts.append(
            f"Extra @output methods not in {element_class.__name__} OUTPUT_NAMES: {sorted(extra_methods)}"
        )

    assert not error_parts, "\n".join(error_parts)
