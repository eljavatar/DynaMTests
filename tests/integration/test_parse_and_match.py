"""Integration tests for the parse -> match -> export chain (TEST_PLAN B.10, I-04..I-06).

Target
------
Three collaborating functions of
[`find_map_tests_cases_from_repo.py`](find_map_tests_cases_from_repo.py:1):

* [`parse_test_cases()`](find_map_tests_cases_from_repo.py:512) — test class ->
  list of test-case dicts (adds the ``class`` metadata and drops 12 raw keys).
* [`parse_potential_focal_methods()`](find_map_tests_cases_from_repo.py:552) —
  focal class -> list of candidate methods enriched with the dynamic context
  (``external_dependencies``, ``class_private_deps_used``, ...).
* [`match_test_cases()`](find_map_tests_cases_from_repo.py:581) — the three
  heuristics that pair them.
* [`export_mtc()`](find_map_tests_cases_from_repo.py:679) /
  [`export()`](find_map_tests_cases_from_repo.py:713) — one JSON file per mapped
  test case.

Real ``ClassParser`` / ``DependencyClassParser`` / ``DependencyParserUtils``
instances run over a ``tmp_path`` copy of ``000_java_classes_prueba``; no
hand-written dicts are involved (unlike the U-MAP unit block).

Module acquisition
------------------
``find_map_tests_cases_from_repo.py`` indexes ``os.environ`` at import time
([`find_map_tests_cases_from_repo.py:32-33`](find_map_tests_cases_from_repo.py:32)),
so it is obtained **only** through the ``fm_repo_module`` fixture.

Deviation from the plan (I-06) — pinned, not fixed
--------------------------------------------------
``TEST_PLAN.md`` expects each exported JSON to have a ``focal_method`` **without**
``body`` / ``external_dependencies`` / ``class_private_deps_used``, and a
``focal_class`` that "keeps ``external_dependencies`` at method level". The
observed behaviour is the **opposite**, and the plan's expectation is
unreachable without touching production code:

* [`find_map_tests_cases_from_repo.py:688-689`](find_map_tests_cases_from_repo.py:688)
  turns ``focal_method`` into the record's own ``focal_method`` value by only
  popping its ``class`` key, keeping ``body``, ``external_dependencies``,
  ``class_private_deps_used``, ...
* the cleaning loop at
  [`find_map_tests_cases_from_repo.py:693-701`](find_map_tests_cases_from_repo.py:693)
  pops those eight keys from every entry of ``focal_class['methods']``, not from
  ``focal_method``. This works because
  [`parse_potential_focal_methods()`](find_map_tests_cases_from_repo.py:562-574)
  stores ``dict(parsed_method)`` (a shallow copy) in the candidate list while
  ``focal_class['methods']`` keeps the original method dicts.

I-06 therefore pins the observed shape (``focal_method`` still carries the raw
keys; ``focal_class['methods']`` is sanitised) and documents the leak here.
"""

from __future__ import annotations

import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

pytestmark = [pytest.mark.integration]

#: Fixture-relative locations of the class under test and of the test class.
TEST_CLASS_RELATIVE = "src/test/com/eljavatar/focals/FocalContextTest.java"
FOCAL_CLASS_RELATIVE = "src/main/com/eljavatar/focals/FocalContext.java"

#: ``@Test`` methods of ``FocalContextTest.java``, in declaration order.
TEST_CASE_NAMES = [
    "testDoSomething",
    "DoSomethingTest",
    "verifyBehaviour",
    "runSomeVoidTest",
    "verifyAmbiguous",
    "verifyNoInvocation",
    "verifyOtherClass",
]

#: The four test cases the heuristics map in a full pass (TEST_PLAN B.4 summary).
MAPPED_TEST_CASE_NAMES = [
    "testDoSomething",
    "DoSomethingTest",
    "verifyBehaviour",
    "runSomeVoidTest",
]

#: The three test cases that must stay unmapped.
UNMAPPED_TEST_CASE_NAMES = {
    "verifyAmbiguous",  # two invocations on the focal class
    "verifyNoInvocation",  # zero invocations
    "verifyOtherClass",  # invocation belongs to another class
}

#: The 12 keys removed in place by ``parse_test_cases()``
#: ([`find_map_tests_cases_from_repo.py:532-545`](find_map_tests_cases_from_repo.py:532)).
REMOVED_TEST_CASE_KEYS = (
    "use_some_field",
    "var_declars",
    "class_fields_used",
    "class_method_references_used",
    "class_methods_used",
    "used_external_dependencies",
    "methods_from_external_dependencies",
    "method_references_from_external_dependencies",
    "fields_from_external_dependencies",
    "field_dependencies_by_class",
    "undefined_method_dependencies",
    "class_methods_that_invoke_other_methods",
)

#: Exact key set of a test case produced by ``parse_test_cases()`` on
#: tree-sitter / tree-sitter-java 0.23.2 (the 12 removed keys excluded, ``class``
#: and the two ``*_by_class`` dependency maps kept).
EXPECTED_TEST_CASE_KEYS = frozenset(
    {
        "body",
        "class",
        "class_method_signature",
        "full_signature",
        "full_signature_parameters",
        "is_constructor",
        "is_get_or_set",
        "is_testcase",
        "method_dependencies_by_class",
        "method_name",
        "method_references_dependencies_by_class",
        "modifiers",
        "parameters",
        "parameters_list",
        "return",
        "signature",
        "test_use_mockito",
        "type_parameters",
    }
)

#: Keys ``export_mtc()`` pops from every method of ``focal_class['methods']``
#: ([`find_map_tests_cases_from_repo.py:693-701`](find_map_tests_cases_from_repo.py:693)).
CLEANED_FOCAL_CLASS_METHOD_KEYS = (
    "body",
    "class",
    "used_private_signatures_of_class",
    "used_non_private_signatures_of_class",
    "class_private_deps_used",
    "class_non_private_deps_used",
    "signatures_of_external_dependencies",
    "external_dependencies",
)

#: Observed ``parameters`` of the two focal methods reached by the heuristics
#: (full signatures: ``name(param_types)``, see U-MAP notes).
DO_SOMETHING_PARAMETERS = (
    "doSomething(Map.Entry<String,@NullableString>, List<ExternalContext01>, "
    "ExternalContext01, Map.Entry<String,ExternalContext01>, Object[])"
)
RUN_SOME_VOID_PARAMETERS = "runSomeVoid(String)"


def _parse_fixture_inputs(
    fm_repo_module,
    class_parser,
    dependency_class_parser,
    dependency_parser_utils,
    java_tmp_tree: Path,
) -> Tuple[Path, Path, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Parse the real fixture project: ``(test_file, focal_file, test_cases, focal_methods)``."""
    test_file = java_tmp_tree / TEST_CLASS_RELATIVE
    focal_file = java_tmp_tree / FOCAL_CLASS_RELATIVE
    assert test_file.is_file(), f"missing fixture file: {test_file}"
    assert focal_file.is_file(), f"missing fixture file: {focal_file}"

    all_focal_java_files = sorted(
        path.as_posix() for path in (java_tmp_tree / "src" / "main").rglob("*.java")
    )

    test_cases = fm_repo_module.parse_test_cases(class_parser, str(test_file))
    focal_methods = fm_repo_module.parse_potential_focal_methods(
        class_parser,
        dependency_class_parser,
        dependency_parser_utils,
        str(focal_file),
        all_focal_java_files,
    )
    return test_file, focal_file, test_cases, focal_methods


def _match_all(
    fm_repo_module,
    dependency_parser_utils,
    test_cases: List[Dict[str, Any]],
    focal_methods: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], str]:
    """Run ``match_test_cases()`` over every parsed test case; return ``(mapped, log_text)``."""
    assert focal_methods, "parse_potential_focal_methods() returned no candidate method"
    log = io.StringIO()
    mapped = fm_repo_module.match_test_cases(
        dependency_parser_utils,
        test_cases[0]["class"],
        focal_methods[0]["class"],
        test_cases,
        focal_methods,
        log,
    )
    return mapped, log.getvalue()


def test_i_04_parse_test_cases_returns_seven_trimmed_test_cases(
    java_tmp_tree: Path,
    fm_repo_module,
    class_parser,
) -> None:
    """I-04: the seven ``@Test`` methods, 12 raw keys removed, ``class`` attached."""
    test_file = java_tmp_tree / TEST_CLASS_RELATIVE
    assert test_file.is_file(), f"missing fixture file: {test_file}"

    test_cases = fm_repo_module.parse_test_cases(class_parser, str(test_file))

    assert len(test_cases) == 7
    assert [test_case["method_name"] for test_case in test_cases] == TEST_CASE_NAMES

    for test_case in test_cases:
        assert test_case["is_testcase"] is True
        assert test_case["body"].strip(), f"empty body for {test_case['method_name']}"

        # ``class`` metadata is attached at
        # [`find_map_tests_cases_from_repo.py:525-530`](find_map_tests_cases_from_repo.py:525)
        assert "class" in test_case
        test_class = test_case["class"]
        assert test_class["class_name"] == "FocalContextTest"
        assert test_class["file"] == str(test_file)
        assert "methods" not in test_class
        assert "argument_list" not in test_class

        # The 12 removed keys are gone; the dependency maps survive because the
        # match heuristics still read them
        # ([`find_map_tests_cases_from_repo.py:541-542`](find_map_tests_cases_from_repo.py:541)).
        for removed_key in REMOVED_TEST_CASE_KEYS:
            assert removed_key not in test_case
        assert "method_dependencies_by_class" in test_case
        assert "method_references_dependencies_by_class" in test_case

        assert frozenset(test_case) == EXPECTED_TEST_CASE_KEYS


def test_i_05_parse_and_match_maps_four_of_seven_test_cases(
    java_tmp_tree: Path,
    fm_repo_module,
    class_parser,
    dependency_class_parser,
    dependency_parser_utils,
) -> None:
    """I-05: real parsing + the three heuristics -> exactly the four expected pairs."""
    _test_file, _focal_file, test_cases, focal_methods = _parse_fixture_inputs(
        fm_repo_module,
        class_parser,
        dependency_class_parser,
        dependency_parser_utils,
        java_tmp_tree,
    )

    assert len(test_cases) == 7
    assert len(focal_methods) == 12  # FocalContext: 2 constructors + 10 methods

    mapped, log_text = _match_all(
        fm_repo_module, dependency_parser_utils, test_cases, focal_methods
    )

    assert len(mapped) == 4
    assert [entry["test_case"]["method_name"] for entry in mapped] == MAPPED_TEST_CASE_NAMES
    assert {
        entry["test_case"]["method_name"] for entry in mapped
    }.isdisjoint(UNMAPPED_TEST_CASE_NAMES)

    assert Counter(entry["focal_method"]["method_name"] for entry in mapped) == Counter(
        {"doSomething": 2, "runSomeVoid": 2}
    )
    assert Counter(entry["focal_method"]["parameters"] for entry in mapped) == Counter(
        {DO_SOMETHING_PARAMETERS: 2, RUN_SOME_VOID_PARAMETERS: 2}
    )

    # Every mapped entry points at the focal class of the fixture
    for entry in mapped:
        assert entry["focal_class"]["class_name"] == "FocalContext"
        assert entry["focal_class"]["file"] == str(_focal_file)
        # The match heuristics consume both dependency maps in place
        assert "method_dependencies_by_class" not in entry["test_case"]
        assert "method_references_dependencies_by_class" not in entry["test_case"]

    assert "Test-Cases: 7" in log_text
    assert "Mapped Test Cases: 4" in log_text
    assert (
        f"> [Single-Invocation] Found Focal-Method: {RUN_SOME_VOID_PARAMETERS}"
        in log_text
    )


def test_i_06_export_mtc_writes_one_json_per_mapped_test_case(
    tmp_path: Path,
    java_tmp_tree: Path,
    fm_repo_module,
    class_parser,
    dependency_class_parser,
    dependency_parser_utils,
) -> None:
    """I-06: four ``123_<n>.json`` files with the five top-level keys."""
    _test_file, _focal_file, test_cases, focal_methods = _parse_fixture_inputs(
        fm_repo_module,
        class_parser,
        dependency_class_parser,
        dependency_parser_utils,
        java_tmp_tree,
    )
    mapped, _log_text = _match_all(
        fm_repo_module, dependency_parser_utils, test_cases, focal_methods
    )
    assert len(mapped) == 4

    repo = {"repo_id": "123", "url": "https://example.invalid/x"}
    output = tmp_path / "mtc"
    output.mkdir()

    fm_repo_module.export_mtc(repo, [mapped], str(output))

    files = sorted(output.glob("*.json"))
    assert [path.name for path in files] == ["123_0.json", "123_1.json", "123_2.json", "123_3.json"]

    expected_pairs = [
        ("testDoSomething", "doSomething", DO_SOMETHING_PARAMETERS),
        ("DoSomethingTest", "doSomething", DO_SOMETHING_PARAMETERS),
        ("verifyBehaviour", "runSomeVoid", RUN_SOME_VOID_PARAMETERS),
        ("runSomeVoidTest", "runSomeVoid", RUN_SOME_VOID_PARAMETERS),
    ]

    for path, (test_case_name, focal_method_name, parameters) in zip(files, expected_pairs):
        data = json.loads(path.read_text(encoding="utf-8"))

        # The five top-level keys of an exported MTC
        assert set(data) == {
            "test_class",
            "test_case",
            "focal_class",
            "focal_method",
            "repository",
        }
        assert data["repository"] == repo

        # ``class`` is moved from the method dicts to the record level
        assert "class" not in data["test_case"]
        assert "class" not in data["focal_method"]
        assert data["test_class"]["class_name"] == "FocalContextTest"
        assert data["focal_class"]["class_name"] == "FocalContext"

        assert data["test_case"]["method_name"] == test_case_name
        assert data["focal_method"]["method_name"] == focal_method_name
        assert data["focal_method"]["parameters"] == parameters

        # Pinned divergence (see module docstring): the top-level ``focal_method``
        # is NOT sanitised, only ``focal_class['methods']`` is
        # ([`find_map_tests_cases_from_repo.py:687-701`](find_map_tests_cases_from_repo.py:687)).
        assert {"body", "external_dependencies", "class_private_deps_used"} <= set(
            data["focal_method"]
        )

        assert data["focal_class"]["methods"], "focal_class['methods'] must not be empty"
        for focal_class_method in data["focal_class"]["methods"]:
            for cleaned_key in CLEANED_FOCAL_CLASS_METHOD_KEYS:
                assert cleaned_key not in focal_class_method

    # ``export()`` removes an existing file before writing
    # ([`find_map_tests_cases_from_repo.py:717-718`](find_map_tests_cases_from_repo.py:717)):
    # a second export overwrites in place and keeps the 0..3 numbering.
    fm_repo_module.export_mtc(repo, [mapped], str(output))
    assert [path.name for path in sorted(output.glob("*.json"))] == [
        "123_0.json",
        "123_1.json",
        "123_2.json",
        "123_3.json",
    ]
