"""Integration tests for ``find_map_test_cases()`` (TEST_PLAN section B.10, I-01..I-03).

Target
------
[`find_map_tests_cases_from_repo.find_map_test_cases()`](find_map_tests_cases_from_repo.py:192),
the orchestrator of stage 1 (stage 1 = "find + map" over a cloned repository).

What is exercised
-----------------
1. **I-01** — the *happy path*: one ``@Test`` class that perfectly matches a
   focal class by name, so the 7 test cases are parsed, 4 of them are mapped and
   the artifacts (``log.txt`` + the ``<repo_id>_<n>.json`` files emitted by
   [`export_mtc()`](find_map_tests_cases_from_repo.py:679)) land in the output
   directory.
2. **I-02** — the repository root does not exist: the early return at
   [`find_map_tests_cases_from_repo.py:209-216`](find_map_tests_cases_from_repo.py:209)
   must report ``repo_exists = False``.
3. **I-03** — ``grep`` finds no ``@Test`` (``CalledProcessError`` with
   ``returncode == 1``): the handler at
   [`find_map_tests_cases_from_repo.py:223-237`](find_map_tests_cases_from_repo.py:223)
   must report ``repo_has_test_files = False`` without flagging an error.

Hermeticity (no network, no ``grep``, no clone)
-----------------------------------------------
* ``find_map_test_cases()`` shells out to ``grep`` through
  ``subprocess.check_output``
  ([`find_map_tests_cases_from_repo.py:219-222`](find_map_tests_cases_from_repo.py:219)).
  Every test replaces ``fm_repo_module.subprocess.check_output`` with a
  deterministic fake (a byte payload for I-01, a ``CalledProcessError`` for
  I-03). ``monkeypatch`` restores the real ``check_output`` on teardown, so no
  other test in the suite is affected.
* No clone happens: ``find_map_test_cases()`` is called directly (the cloning
  lives in ``analyze_project()`` / ``clone_repo()``, which these tests never
  reach). The autouse ``no_network`` fixture stays active.
* ``find_map_test_cases()`` calls ``os.chdir(root)``
  ([`find_map_tests_cases_from_repo.py:210`](find_map_tests_cases_from_repo.py:210))
  and never restores the previous working directory, so every test first calls
  ``monkeypatch.chdir(...)``; ``monkeypatch`` puts the original cwd back even
  after the production ``os.chdir``.

Deviation from the plan (I-01) — pinned, not fixed
--------------------------------------------------
``TEST_PLAN.md`` describes root as "tree with ``src/main/...`` and
``src/test/...``". That layout does **not** produce a match, because the
test-class normalisation at
[`find_map_tests_cases_from_repo.py:289`](find_map_tests_cases_from_repo.py:289)
is ``test_class.lower().replace("/src/test/", "/src/main/")``: the ``/src/test/``
segment must be preceded by another path component (the project folder), while
the ``focal_files`` side strips that component only of the ``"./"`` prefix
([`find_map_tests_cases_from_repo.py:259`](find_map_tests_cases_from_repo.py:259)).
Therefore the production contract is: **``root`` must be the parent of the
project directory**, and ``grep`` must return paths *relative to ``root``*
(``<project>/src/test/...``, exactly what ``grep -r`` prints when run from
``root``). I-01 uses ``root = java_tmp_tree.parent`` together with a fake
listing prefixed by the project folder name, which is the hermetic equivalent of
a real repository checkout. With ``root = java_tmp_tree`` the perfect-match
stage finds 0 focal classes and the function returns ``(1, 0, 0, 0, ...)``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict

import pytest

pytestmark = [pytest.mark.integration]

#: Relative location of the single test class of the fixture project.
TEST_CLASS_RELATIVE = "src/test/com/eljavatar/focals/FocalContextTest.java"

#: Message written by the "repository not found" branch
#: ([`find_map_tests_cases_from_repo.py:213`](find_map_tests_cases_from_repo.py:213)).
REPO_NOT_EXISTS_MESSAGE = "Path repo not exists: "

#: Message written by the "no @Test annotations" branch
#: ([`find_map_tests_cases_from_repo.py:227`](find_map_tests_cases_from_repo.py:227)).
NO_TEST_ANNOTATION_MESSAGE = (
    "No se encontraron archivos .java que contengan la anotacion @Test"
)


def _fake_check_output(payload: bytes):
    """Return a ``subprocess.check_output`` replacement that always returns *payload*."""

    def _check_output(*_args: Any, **_kwargs: Any) -> bytes:
        return payload

    return _check_output


def _fake_check_output_no_matches(*_args: Any, **_kwargs: Any) -> bytes:
    """Return a ``subprocess.check_output`` replacement emulating ``grep`` with no hits."""
    raise subprocess.CalledProcessError(1, "grep")


def _repo_from_payload(payload) -> Dict[str, str]:
    """Build the ``repo`` dict from ``tests/fixtures/repos_prueba.json`` entry 0.

    Only ``repo_id`` / ``url`` are consumed: ``find_map_test_cases()`` writes them
    into ``log.txt`` and uses ``repo_id`` as the JSON file prefix. No clone is
    attempted, so the (real) URL stays inert.
    """
    entry = payload[0]
    return {"repo_id": str(entry["repo_id"]), "url": str(entry["url"])}


def test_i_01_finds_test_class_and_maps_four_test_cases(
    tmp_path: Path,
    java_tmp_tree: Path,
    fm_repo_module,
    monkeypatch: pytest.MonkeyPatch,
    repo_prueba_payload,
) -> None:
    """I-01: one test class -> one focal class -> 4 mapped test cases, artifacts written."""
    repo = _repo_from_payload(repo_prueba_payload)

    # ``find_map_test_cases()`` chdirs into ``root`` and globs relative paths, so
    # ``root`` is the parent folder of the project (see the module docstring).
    repo_root = java_tmp_tree.parent
    project_dir_name = java_tmp_tree.name
    test_listing = f"{project_dir_name}/{TEST_CLASS_RELATIVE}\n"

    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        fm_repo_module.subprocess,
        "check_output",
        _fake_check_output(test_listing.encode("ascii")),
    )

    output = tmp_path / "output"
    output.mkdir()

    result = fm_repo_module.find_map_test_cases(
        str(repo_root), "java", str(output), repo, False
    )

    # (tot_tclass, tot_tc, tot_tclass_fclass, tot_mtc, repo_exists,
    #  repo_has_test_files, error_finding_java_files)
    assert result == (1, 7, 1, 4, True, True, False)

    log_path = output / "log.txt"
    assert log_path.is_file()
    log_text = log_path.read_text(encoding="utf-8")
    assert f"REPOSITORY {repo['repo_id']} ({repo['url']})" in log_text
    assert "Perfect Matches Found: 1" in log_text
    assert "Test-Cases: 7" in log_text
    assert "Mapped Test Cases: 4" in log_text

    # The mapping loop swallowed no exception, hence the error log is removed
    # ([`find_map_tests_cases_from_repo.py:401-402`](find_map_tests_cases_from_repo.py:401)).
    assert not (output / "log_error_mapping.txt").exists()

    # ``find_map_test_cases()`` exports the mapped test cases itself
    # ([`find_map_tests_cases_from_repo.py:387-389`](find_map_tests_cases_from_repo.py:387)).
    assert sorted(path.name for path in output.glob("*.json")) == [
        f"{repo['repo_id']}_{index}.json" for index in range(4)
    ]


def test_i_02_missing_repository_root_reports_repo_not_exists(
    tmp_path: Path,
    fm_repo_module,
) -> None:
    """I-02: a non-existing ``root`` short-circuits with ``repo_exists = False``."""
    output = tmp_path / "output"
    output.mkdir()
    missing_root = tmp_path / "missing_repo"
    assert not missing_root.exists()

    result = fm_repo_module.find_map_test_cases(
        str(missing_root),
        "java",
        str(output),
        {"repo_id": "999", "url": "https://example.invalid/missing"},
        False,
    )

    assert result == (0, 0, 0, 0, False, True, True)

    log_text = (output / "log.txt").read_text(encoding="utf-8")
    assert f"{REPO_NOT_EXISTS_MESSAGE}{missing_root}" in log_text
    assert not (output / "log_error_mapping.txt").exists()
    assert list(output.glob("*.json")) == []


def test_i_03_grep_without_test_annotations_reports_no_test_files(
    tmp_path: Path,
    java_tmp_tree: Path,
    fm_repo_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """I-03: ``grep`` exit code 1 (no ``@Test``) is not an error, only a negative flag."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        fm_repo_module.subprocess, "check_output", _fake_check_output_no_matches
    )

    output = tmp_path / "output"
    output.mkdir()

    result = fm_repo_module.find_map_test_cases(
        str(java_tmp_tree),
        "java",
        str(output),
        {"repo_id": "123", "url": "https://example.invalid/x"},
        False,
    )

    assert result == (0, 0, 0, 0, True, False, False)

    log_text = (output / "log.txt").read_text(encoding="utf-8")
    assert NO_TEST_ANNOTATION_MESSAGE in log_text
    assert not (output / "log_error_mapping.txt").exists()
