"""
Module entry for future modular FastAPI app.
Current phase keeps compatibility by re-exporting legacy app.
"""

import importlib.util
import pathlib

_legacy_path = pathlib.Path("/home/hyfree/todo-server-fastapi.py")
_spec = importlib.util.spec_from_file_location("legacy_todo_server", _legacy_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError("Cannot load legacy server module")

_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
