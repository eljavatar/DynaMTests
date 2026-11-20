"""Load project modules from explicit filesystem paths under stable aliases.

The DynaMTests pipeline is made of top-level scripts (``build_corpus.py``,
``build_corpus_d4j.py``, ``find_map_tests_cases_from_repo.py``, ...) that are
not part of an importable package and that share function names between them
(for example ``build_format_corpus`` exists twice).  Loading them with
``importlib.util.spec_from_file_location`` and a unique alias lets a single
pytest process hold both copies at once without polluting ``sys.modules`` with
colliding names.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable, Union

__all__ = ["load_module_from_path", "reload_module_from_path"]


def load_module_from_path(
    path: Union[str, Path],
    alias: str,
    extra_sys_path: Iterable[Union[str, Path]] = (),
) -> ModuleType:
    """Import the Python file at *path* and register it in ``sys.modules`` as *alias*.

    Parameters
    ----------
    path:
        Python source file to load.
    alias:
        Unique module name used for registration.  It must not collide with a
        top-level module of the project.
    extra_sys_path:
        Optional directories inserted at the front of ``sys.path`` before
        executing the module (the project root is enough in almost every case).
    """
    resolved_path = Path(path).resolve()
    if not resolved_path.is_file():
        raise FileNotFoundError(f"Module file not found: {resolved_path}")

    for entry in extra_sys_path:
        entry_str = str(Path(entry).resolve())
        if entry_str not in sys.path:
            sys.path.insert(0, entry_str)

    already_loaded = sys.modules.get(alias)
    if already_loaded is not None and getattr(already_loaded, "__file__", None) == str(resolved_path):
        return already_loaded

    spec = importlib.util.spec_from_file_location(alias, str(resolved_path))
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot build an import spec for: {resolved_path}")

    module = importlib.util.module_from_spec(spec)
    # Register before executing so that dataclasses/typing forward references
    # and intra-module imports of the script resolve correctly.
    sys.modules[alias] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(alias, None)
        raise
    return module


def reload_module_from_path(
    path: Union[str, Path],
    alias: str,
    extra_sys_path: Iterable[Union[str, Path]] = (),
) -> ModuleType:
    """Force a fresh load of *path* under *alias* (drops any previous instance)."""
    sys.modules.pop(alias, None)
    return load_module_from_path(path, alias, extra_sys_path=extra_sys_path)
