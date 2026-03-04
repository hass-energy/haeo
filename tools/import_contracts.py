"""Custom import-linter contract: allowlist."""

from __future__ import annotations

import sys
from typing import Any

from grimp import ImportGraph
from importlinter.application import output
from importlinter.domain import fields
from importlinter.domain.contract import Contract, ContractCheck
from importlinter.domain.imports import Module

_EXTERNAL_PACKAGES_MSG = "The top level configuration must have include_external_packages=True for allowlist contracts."


class AllowlistContract(Contract):
    """Contract that only permits imports from an explicit allowlist.

    Source modules may import from:
    - Other modules within the same source package (internal imports)
    - Standard library modules
    - Modules whose top-level package is in the allowlist

    Everything else (sibling packages, external packages not listed) is a violation.
    """

    type_name = "allowlist"

    source_modules = fields.SetField(subfield=fields.ModuleExpressionField())
    allow_modules = fields.SetField(subfield=fields.StringField())

    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        """Check that source modules only import from allowed modules."""
        if not self._graph_was_built_with_externals():
            raise ValueError(_EXTERNAL_PACKAGES_MSG)

        source_module_names = self._resolve_source_modules(graph)
        allowed: set[Any] = self.allow_modules  # type: ignore[assignment]
        disallowed: dict[str, list[dict[str, object]]] = {}

        for module_name in sorted(source_module_names):
            output.verbose_print(verbose, f"Checking imports from {module_name}...")
            for imported_name in graph.find_modules_directly_imported_by(module_name):
                if imported_name in source_module_names:
                    continue
                if self._is_allowed(imported_name, allowed):
                    continue

                import_details = graph.get_import_details(importer=module_name, imported=imported_name)
                line_numbers = tuple(d["line_number"] for d in import_details)
                disallowed.setdefault(module_name, []).append({"imported": imported_name, "line_numbers": line_numbers})

        return ContractCheck(
            kept=not disallowed,
            metadata={"disallowed": disallowed, "allowed": sorted(str(m) for m in allowed)},
        )

    def render_broken_contract(self, check: ContractCheck) -> None:
        """Render the details of a broken allowlist contract."""
        allowed = check.metadata["allowed"]
        output.print_error(f"Allowed imports: {', '.join(allowed)}", bold=False)
        output.new_line()
        output.print_error("Disallowed imports found:", bold=True)
        output.new_line()

        for module, imports in sorted(check.metadata["disallowed"].items()):
            for imp in imports:
                lines = ", ".join(f"l.{n}" if n is not None else "l.?" for n in imp["line_numbers"])
                output.print_error(f"  {module} -> {imp['imported']} ({lines})", bold=False)
            output.new_line()

    def _resolve_source_modules(self, graph: ImportGraph) -> set[str]:
        source_names: set[str] = set()
        for expression in self.source_modules:  # type: ignore[union-attr]
            module = Module(str(expression))
            source_names.add(module.name)
            if not graph.is_module_squashed(module.name):
                source_names |= set(graph.find_descendants(module.name))
        return {n for n in source_names if not _is_test_module(n)}

    @staticmethod
    def _is_allowed(imported: str, allowed_prefixes: set[str]) -> bool:
        top_level = imported.split(".")[0]
        if top_level in sys.stdlib_module_names:
            return True
        return any(imported == prefix or imported.startswith(prefix + ".") for prefix in allowed_prefixes)

    def _graph_was_built_with_externals(self) -> bool:
        return str(self.session_options.get("include_external_packages")).lower() == "true"


def _is_test_module(name: str) -> bool:
    parts = name.split(".")
    return any(p.startswith("test_") or p in ("conftest", "tests") for p in parts)
