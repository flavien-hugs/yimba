"""Rules the import-linter contracts cannot express: modules talk to each other through ``public`` only."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "yimba"
MODULES = SRC / "modules"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
    return names


def test_modules_only_use_each_others_public_surface():
    offenders = []
    for path in MODULES.rglob("*.py"):
        own = path.relative_to(MODULES).parts[0]
        for imported in _imports(path):
            parts = imported.split(".")
            if parts[:2] != ["yimba", "modules"] or len(parts) < 3 or parts[2] == own:
                continue
            if len(parts) < 4 or parts[3] != "public":
                offenders.append(f"{path.relative_to(SRC)} imports {imported}")
    assert not offenders, "\n".join(offenders)


def test_every_module_has_the_hexagonal_layers_and_a_public_surface():
    for module in sorted(p for p in MODULES.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for layer in ("domain", "application", "adapters"):
            assert (module / layer / "__init__.py").exists(), f"{module.name} lacks {layer}"
        assert (module / "public.py").exists(), f"{module.name} lacks public.py"
