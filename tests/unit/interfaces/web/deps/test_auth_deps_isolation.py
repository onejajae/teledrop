import ast
from pathlib import Path

import app.interfaces.web.deps.auth as web_auth_deps


def test_web_auth_deps_do_not_import_api_deps():
    tree = ast.parse(Path(web_auth_deps.__file__).read_text(encoding="utf-8"))

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)

    assert not any(
        module.startswith("app.interfaces.api.deps") for module in imported_modules
    )
