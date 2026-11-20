"""Shared pytest fixtures for the DynaMTests test suite.

This module is the single place that runs *before* any test module imports a
production script, therefore it:

1. Defines ``GITHUB_USER`` / ``GITHUB_TOKEN`` via ``os.environ.setdefault`` at
   module import time. ``find_map_tests_cases_from_repo.py`` reads both keys by
   direct indexing at import time (``find_map_tests_cases_from_repo.py:32-33``),
   so without this the import raises ``KeyError``.
2. Inserts the repository root and the ``tests/`` folder at the front of
   ``sys.path`` so the flat scripts (``ClassParser``, ``ParserUtils``,
   ``build_corpus``, ...) and the local helper packages are importable without
   installing anything.
3. Provides hermetic fixtures: every output path is created below ``tmp_path``
   and no fixture touches ``corpus/``, ``dataset/``, ``repos/``,
   ``defects4j_corpus/`` or ``mining_results/``.

Nothing here modifies production behaviour.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import socket
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import pytest

# ---------------------------------------------------------------------------
# 1) Bootstrap: must happen before production modules are imported.
# ---------------------------------------------------------------------------
os.environ.setdefault("GITHUB_USER", "test-user")
os.environ.setdefault("GITHUB_TOKEN", "test-token")

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent

for _entry in (str(REPO_ROOT), str(TESTS_DIR)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from helpers.module_loader import load_module_from_path  # noqa: E402  (needs sys.path above)

# Stable aliases so that different copies of same-named modules can coexist.
FM_REPO_ALIAS = "dynamtests_find_map"
BUILD_CORPUS_ALIAS = "dynamtests_build_corpus"
BUILD_CORPUS_D4J_ALIAS = "dynamtests_build_corpus_d4j"
CLEAN_DUPLICATES_ALIAS = "dynamtests_clean_duplicates"
CONVERT_CSV_ALIAS = "dynamtests_convert_csv"


# ---------------------------------------------------------------------------
# Global / environment fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def env_github() -> None:
    """Ensure the GitHub credentials read at import time exist (obstacle O1)."""
    os.environ.setdefault("GITHUB_USER", "test-user")
    os.environ.setdefault("GITHUB_TOKEN", "test-token")
    yield


@pytest.fixture(scope="session", autouse=True)
def no_network() -> None:
    """Fail loudly if any test tries to reach the network (test E-02)."""
    mp = pytest.MonkeyPatch()

    def _forbidden(*_args: Any, **_kwargs: Any):
        raise AssertionError(
            "Network access is forbidden in the DynaMTests test suite. "
            "Use tmp_path-based fixtures instead of remote resources."
        )

    mp.setattr(socket.socket, "connect", _forbidden)
    mp.setattr(socket.socket, "connect_ex", _forbidden)
    mp.setattr(socket, "create_connection", _forbidden)

    try:  # urllib is always available, but be defensive anyway
        import urllib.request as _urllib_request

        mp.setattr(_urllib_request, "urlopen", _forbidden)
    except ImportError:  # pragma: no cover
        pass

    try:  # GitPython is an optional runtime dependency of the suite
        import git as _git

        mp.setattr(_git.Repo, "clone_from", staticmethod(_forbidden))
    except ImportError:  # pragma: no cover
        pass

    _requests = sys.modules.get("requests")
    if _requests is not None:  # pragma: no cover - only when requests is imported
        mp.setattr(_requests.sessions.Session, "request", _forbidden, raising=False)

    yield
    mp.undo()


# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path of the project root directory."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def tests_root() -> Path:
    """Absolute path of the ``tests/`` directory."""
    return TESTS_DIR


@pytest.fixture(scope="session")
def myclass_java_path(repo_root: Path) -> Path:
    """Path of the reference fixture ``MyClass.java`` at the project root."""
    path = repo_root / "MyClass.java"
    if not path.is_file():
        pytest.skip(f"Missing fixture: {path}")
    return path


@pytest.fixture(scope="session")
def java_classes_root(repo_root: Path) -> Path:
    """Root of the ``000_java_classes_prueba`` fixture project."""
    path = repo_root / "000_java_classes_prueba"
    if not path.is_dir():
        pytest.skip(f"Missing fixture project: {path}")
    return path


@pytest.fixture(scope="session")
def java_main_root(java_classes_root: Path) -> Path:
    """``000_java_classes_prueba/src/main`` directory."""
    return java_classes_root / "src" / "main"


@pytest.fixture(scope="session")
def java_test_root(java_classes_root: Path) -> Path:
    """``000_java_classes_prueba/src/test`` directory."""
    return java_classes_root / "src" / "test"


@pytest.fixture(scope="session")
def focal_context_java(java_main_root: Path) -> Path:
    """``FocalContext.java`` fixture file."""
    path = java_main_root / "com" / "eljavatar" / "focals" / "FocalContext.java"
    if not path.is_file():
        pytest.skip(f"Missing fixture: {path}")
    return path


@pytest.fixture(scope="session")
def focal_context_test_java(java_test_root: Path) -> Path:
    """``FocalContextTest.java`` fixture added for the mapeo tests (TEST_PLAN C.3)."""
    path = java_test_root / "com" / "eljavatar" / "focals" / "FocalContextTest.java"
    if not path.is_file():
        pytest.skip(f"Missing fixture: {path}")
    return path


@pytest.fixture(scope="session")
def broken_java_source(tests_root: Path) -> Path:
    """Malformed Java source used by the ``parse_file`` error-path tests."""
    path = tests_root / "fixtures" / "java" / "BrokenClass.java.txt"
    if not path.is_file():
        pytest.skip(f"Missing fixture: {path}")
    return path


@pytest.fixture
def broken_java_file(tmp_path: Path, broken_java_source: Path) -> Path:
    """A ``.java`` copy of the malformed source inside ``tmp_path``."""
    destination = tmp_path / "broken" / "BrokenClass.java"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(broken_java_source, destination)
    return destination


# ---------------------------------------------------------------------------
# tree-sitter helpers (independent of the production parsers)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def ts_java():
    """``tree_sitter_java`` module (skips when the dependency is missing)."""
    return pytest.importorskip("tree_sitter_java")


@pytest.fixture(scope="session")
def java_language(ts_java):
    """``tree_sitter.Language`` instance configured for Java."""
    pytest.importorskip("tree_sitter")
    from importlib.metadata import version as dist_version

    from packaging import version as packaging_version
    from tree_sitter import Language

    tree_sitter_version = dist_version("tree_sitter")
    if packaging_version.parse(tree_sitter_version) < packaging_version.parse("0.22.0"):
        return Language(ts_java.language(), "java")
    return Language(ts_java.language())


@pytest.fixture(scope="session")
def java_parser(java_language):
    """Configured ``tree_sitter.Parser`` for Java (mirrors production setup)."""
    from importlib.metadata import version as dist_version

    from packaging import version as packaging_version
    from tree_sitter import Parser

    tree_sitter_version = dist_version("tree_sitter")
    if packaging_version.parse(tree_sitter_version) < packaging_version.parse("0.22.1"):
        parser = Parser()
        parser.set_language(java_language)
    else:
        parser = Parser(java_language)
    return parser


@pytest.fixture(scope="session")
def parse_java_source(java_parser) -> Callable[[Any], Any]:
    """Return a callable ``parse(source) -> tree`` for ``str``/``bytes``/``Path``."""

    def _parse(source: Any):
        if isinstance(source, Path):
            source = source.read_text(encoding="utf-8")
        if isinstance(source, bytes):
            source_bytes = source
        else:
            source_bytes = str(source).encode("utf-8")
        return java_parser.parse(source_bytes)

    return _parse


# ---------------------------------------------------------------------------
# Production objects (imported lazily so a partial environment yields skips)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def parser_utils():
    """Shared ``ParserUtils('utf-8')`` instance."""
    pytest.importorskip("tree_sitter")
    from ParserUtils import ParserUtils

    return ParserUtils("utf-8")


@pytest.fixture
def class_parser():
    """Fresh ``ClassParser('java')`` (stateful ``content`` attribute)."""
    pytest.importorskip("tree_sitter")
    from ClassParser import ClassParser

    return ClassParser("java")


@pytest.fixture
def dependency_class_parser():
    """Fresh ``DependencyClassParser('java')``."""
    pytest.importorskip("tree_sitter")
    from DependencyClassParser import DependencyClassParser

    return DependencyClassParser("java")


@pytest.fixture(scope="session")
def dependency_parser_utils():
    """``DependencyParserUtils`` container of static helpers."""
    pytest.importorskip("tree_sitter")
    from dependency_parser_utils import DependencyParserUtils

    return DependencyParserUtils()


# ---------------------------------------------------------------------------
# Project scripts loaded under unique aliases (obstacle O2)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def load_project_module() -> Callable[[str, str], Any]:
    """Return ``load(relative_path, alias)`` to import pipeline scripts safely."""

    def _load(relative_path: str, alias: str):
        return load_module_from_path(REPO_ROOT / relative_path, alias, extra_sys_path=[REPO_ROOT])

    return _load


@pytest.fixture(scope="module")
def fm_repo_module(load_project_module):
    """``find_map_tests_cases_from_repo.py`` loaded as ``dynamtests_find_map``."""
    pytest.importorskip("tree_sitter")
    pytest.importorskip("git")
    pytest.importorskip("command_runner")

    module = sys.modules.get(FM_REPO_ALIAS)
    if module is not None and hasattr(module, "parse_args"):
        return module
    if module is not None:  # half-initialised module left by a failed import
        sys.modules.pop(FM_REPO_ALIAS, None)
    return load_project_module("find_map_tests_cases_from_repo.py", FM_REPO_ALIAS)


@pytest.fixture(scope="module")
def build_corpus_module(load_project_module):
    """``build_corpus.py`` loaded as ``dynamtests_build_corpus``."""
    pytest.importorskip("tree_sitter")
    pytest.importorskip("tqdm")
    return load_project_module("build_corpus.py", BUILD_CORPUS_ALIAS)


@pytest.fixture(scope="module")
def build_corpus_d4j_module(load_project_module):
    """``build_corpus_d4j.py`` loaded as ``dynamtests_build_corpus_d4j``."""
    pytest.importorskip("tree_sitter")
    pytest.importorskip("tqdm")
    return load_project_module("build_corpus_d4j.py", BUILD_CORPUS_D4J_ALIAS)


@pytest.fixture(scope="module")
def clean_duplicates_module(load_project_module):
    """``clean_duplicates_and_build_dataset.py`` under a unique alias."""
    pytest.importorskip("tqdm")
    return load_project_module("clean_duplicates_and_build_dataset.py", CLEAN_DUPLICATES_ALIAS)


@pytest.fixture(scope="module")
def convert_csv_module(load_project_module):
    """``convert_json_corpus_to_csv_input.py`` under a unique alias."""
    pytest.importorskip("pandas")
    return load_project_module("convert_json_corpus_to_csv_input.py", CONVERT_CSV_ALIAS)


# ---------------------------------------------------------------------------
# Synthetic data builders and hermetic inputs
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def repo_prueba_payload(repo_root: Path) -> List[Dict[str, Any]]:
    """Parsed content of ``repos_prueba.json`` (15 ``repo_id``/``url`` entries)."""
    path = repo_root / "repos_prueba.json"
    if not path.is_file():
        pytest.skip(f"Missing fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def make_mtc_json() -> Callable[..., Dict[str, Any]]:
    """Return the ``make_mtc_json(...)`` builder of ``fixtures.mining_samples``."""
    from fixtures.mining_samples import make_mtc_json as _make_mtc_json

    return _make_mtc_json


@pytest.fixture
def make_corpus_record() -> Callable[..., Dict[str, str]]:
    """Return the ``make_corpus_record(index)`` builder of ``fixtures.mining_samples``."""
    from fixtures.mining_samples import make_corpus_record as _make_corpus_record

    return _make_corpus_record


# ---------------------------------------------------------------------------
# Java project tree copy
# ---------------------------------------------------------------------------
@pytest.fixture
def java_tmp_tree(tmp_path: Path) -> Path:
    """Copy of ``000_java_classes_prueba`` (``src/main`` + ``src/test``) in ``tmp_path``.

    Returns the project root, so tests build paths such as
    ``java_tmp_tree / "src/main/com/eljavatar/focals/FocalContext.java"``.
    """
    source = REPO_ROOT / "000_java_classes_prueba"
    if not source.is_dir():
        pytest.skip(f"Missing fixture project: {source}")

    destination = tmp_path / "000_java_classes_prueba"
    for split in ("main", "test"):
        split_source = source / "src" / split
        if split_source.is_dir():
            shutil.copytree(split_source, destination / "src" / split)
    return destination


@pytest.fixture
def java_tmp_main(java_tmp_tree: Path) -> Path:
    """``src/main`` of the temporary Java project."""
    return java_tmp_tree / "src" / "main"


@pytest.fixture
def java_tmp_test(java_tmp_tree: Path) -> Path:
    """``src/test`` of the temporary Java project."""
    return java_tmp_tree / "src" / "test"


@pytest.fixture
def all_focal_java_files(java_tmp_tree: Path) -> List[str]:
    """The ten ``.java`` files of ``src/main`` as absolute POSIX paths.

    ``DependencyParserUtils.get_path_imports()`` resolves imports with
    ``file.endswith("package/path/Class.java")`` and later re-opens the strings
    it returns, so absolute POSIX paths work both for matching and for opening
    (this is what ``monkeypatch.chdir(java_tmp_tree)`` would achieve with the
    repo-relative paths produced by ``glob`` in production).
    """
    main_root = java_tmp_tree / "src" / "main"
    return sorted(path.as_posix() for path in main_root.rglob("*.java"))


@pytest.fixture
def java_main_files(java_tmp_tree: Path) -> List[Path]:
    """Absolute paths of the ``.java`` files under ``src/main``."""
    return sorted((java_tmp_tree / "src" / "main").rglob("*.java"))


# ---------------------------------------------------------------------------
# Synthetic mining / corpus trees
# ---------------------------------------------------------------------------
@pytest.fixture
def mining_tmp_tree(tmp_path: Path, make_mtc_json) -> Path:
    """``tmp_path/mining/{train,validation,test}/output/123/`` with 2 mining JSONs each.

    The fixture is a starting point: tests that need controlled contents (for
    example the duplicate-detection cases) may rewrite or remove the files.
    """
    root = tmp_path / "mining"
    repo_id = "123"
    for split in ("train", "validation", "test"):
        repo_dir = root / split / "output" / repo_id
        repo_dir.mkdir(parents=True)
        with_external = make_mtc_json(with_external_dependency=True, repo_id=repo_id)
        without_external = make_mtc_json(
            body_focal='public String helper(int val) { return "x"; }',
            body_test="public void testHelper() { new SampleFocal().doSomething(1); }",
            repo_id=repo_id,
            test_case_name="testHelper",
        )
        (repo_dir / f"{repo_id}_0.json").write_text(
            json.dumps(with_external), encoding="utf-8"
        )
        (repo_dir / f"{repo_id}_1.json").write_text(
            json.dumps(without_external), encoding="utf-8"
        )
    return root


@pytest.fixture
def json_corpus_2_repos(tmp_path: Path, make_corpus_record) -> Path:
    """``corpus/json/validation/{repoA,repoB}`` with one 6-key record each.

    Returns the *split* directory, i.e. the ``corpus_path`` argument expected by
    ``convert_json_corpus_to_csv_input.convert()``.
    """
    split_dir = tmp_path / "corpus" / "json" / "validation"
    split_dir.mkdir(parents=True)
    for index, repo_id in enumerate(("repoA", "repoB")):
        repo_dir = split_dir / repo_id
        repo_dir.mkdir()
        record = make_corpus_record(index)
        (repo_dir / f"{repo_id}_{index}_corpus.json").write_text(
            json.dumps(record, ensure_ascii=False), encoding="utf-8"
        )
    return split_dir


# ---------------------------------------------------------------------------
# Hand-written metadata dictionaries (TEST_PLAN C.2)
# ---------------------------------------------------------------------------
@pytest.fixture
def metadata_focal_context() -> Dict[str, Any]:
    """Canonical ``{focal_class, focal_method}`` dict that produces L1/L2/L3."""
    from fixtures.metadata_samples import metadata_focal_context as _factory

    return _factory()


@pytest.fixture
def metadata_focal_context_no_ext() -> Dict[str, Any]:
    """Variant without external dependencies."""
    from fixtures.metadata_samples import metadata_focal_context_no_ext as _factory

    return _factory()


@pytest.fixture
def metadata_focal_context_no_priv() -> Dict[str, Any]:
    """Variant without private members used by the focal method."""
    from fixtures.metadata_samples import metadata_focal_context_no_priv as _factory

    return _factory()


@pytest.fixture
def metadata_invalid_sig() -> Dict[str, Any]:
    """Variant whose class signature fails validation."""
    from fixtures.metadata_samples import metadata_invalid_sig as _factory

    return _factory()


@pytest.fixture
def metadata_myclass() -> Dict[str, Any]:
    """Metadata for ``MyClass.java`` (annotated, generic, duplicated imports)."""
    from fixtures.metadata_samples import metadata_myclass as _factory

    return _factory()


# ---------------------------------------------------------------------------
# Real (non-hand-written) inputs for ``match_test_cases``
# ---------------------------------------------------------------------------
@pytest.fixture
def match_inputs_real(
    java_tmp_tree: Path,
    class_parser,
    dependency_class_parser,
    dependency_parser_utils,
    fm_repo_module,
) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """``(test_class, focal_class, test_cases, focal_methods)`` parsed from Java.

    Built with the real ``ClassParser`` / ``DependencyParserUtils`` over the
    temporary Java tree, so the mapping heuristics are exercised end to end.
    """
    test_file = java_tmp_tree / "src" / "test" / "com" / "eljavatar" / "focals" / "FocalContextTest.java"
    focal_file = java_tmp_tree / "src" / "main" / "com" / "eljavatar" / "focals" / "FocalContext.java"
    if not test_file.is_file():
        pytest.skip(f"Missing fixture: {test_file}")
    if not focal_file.is_file():
        pytest.skip(f"Missing fixture: {focal_file}")

    all_focal = sorted(
        path.as_posix() for path in (java_tmp_tree / "src" / "main").rglob("*.java")
    )

    test_cases = fm_repo_module.parse_test_cases(class_parser, str(test_file))
    focal_methods = fm_repo_module.parse_potential_focal_methods(
        class_parser,
        dependency_class_parser,
        dependency_parser_utils,
        str(focal_file),
        all_focal,
    )

    test_class = test_cases[0]["class"] if test_cases else {}
    focal_class = focal_methods[0]["class"] if focal_methods else {}
    return test_class, focal_class, test_cases, focal_methods


@pytest.fixture
def tmp_log() -> io.StringIO:
    """In-memory replacement for the ``log`` file handle of ``match_test_cases``."""
    return io.StringIO()
