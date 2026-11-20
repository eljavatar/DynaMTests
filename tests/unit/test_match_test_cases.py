"""Unit tests for ``match_test_cases()`` (TEST_PLAN section B.4, U-MAP-01..U-MAP-10).

Target
------
[`find_map_tests_cases_from_repo.match_test_cases()`](find_map_tests_cases_from_repo.py:581)
and its three heuristics:

1. *Name matching* — [`612-628`](find_map_tests_cases_from_repo.py:612), after the
   ``test`` prefix/suffix normalisation at
   [`603-607`](find_map_tests_cases_from_repo.py:603).
2. *Single invocation* — [`632-666`](find_map_tests_cases_from_repo.py:632), with
   the ambiguous-arity rejection at
   [`644-646`](find_map_tests_cases_from_repo.py:644).
3. *Other-class rejection* — the ``focal_class_name`` filter at
   [`634-642`](find_map_tests_cases_from_repo.py:634).

Module acquisition
------------------
``find_map_tests_cases_from_repo.py`` indexes ``os.environ`` for the GitHub
credentials at import time
([`find_map_tests_cases_from_repo.py:32-33`](find_map_tests_cases_from_repo.py:32)),
so it is obtained **only** through the ``fm_repo_module`` fixture; this file
never imports it at module scope.

Testability notes / pinned divergences from ``tests/TEST_PLAN.md``
------------------------------------------------------------------
1. **``parameters`` is a full signature, not "type name"** — the plan writes
   ``'int val'`` / ``'String val'`` (U-MAP-01/U-MAP-03/U-MAP-06), but
   [`ClassParser.get_function_metadata()`](ClassParser.py:443) initialises
   ``'parameters': ''`` at [`ClassParser.py:455`](ClassParser.py:455) and then
   fills it as ``name(param_types)`` — e.g. ``'runSomeVoid(String)'``. The
   tests below pin the **observed** strings, and additionally assert
   ``parameters_list`` (the arity/type contract) so the assertions stay
   meaningful if the textual format ever changes.
2. **One test case per test** — the fixture
   [`FocalContextTest.java`](tests/fixtures/java/sample_java_repo/src/test/com/eljavatar/focals/FocalContextTest.java:15)
   holds seven ``@Test`` methods while the plan describes
   ``len(mapped) == 1`` (a single-input invocation). The helper ``_match(...)``
   therefore selects the requested test case and passes a one-element list,
   which keeps the plan's cardinality literals valid and isolates one heuristic
   per test. U-MAP-10 exercises all seven methods at once.
3. **U-MAP-06 is the regression lock** for the overload-insensitive
   ``list.index()`` at
   [`find_map_tests_cases_from_repo.py:614`](find_map_tests_cases_from_repo.py:614):
   ``runSomeVoidTest`` invokes ``runSomeVoid(1L)`` yet is mapped to the first
   ``runSomeVoid`` declaration
   ([`FocalContext.java:83`](tests/fixtures/java/sample_java_repo/src/main/com/eljavatar/focals/FocalContext.java:83),
   ``String``) because only *names* are compared. Production code is not
   modified.
4. **U-MAP-07 is an intentional strict ``xfail``** (the Spoon-desired
   resolution by arity/type). It is asserted through ``parameters_list``
   instead of the plan's ``'Long val'`` string, so the desired behaviour is
   expressed independently of the textual ``parameters`` format above.

All work happens on ``tmp_path`` copies of the Java fixture project through the
``match_inputs_real`` fixture; nothing touches the network or a ``.rooignore``d
directory.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Tuple

import pytest

pytestmark = pytest.mark.unit

#: ``parameters`` of ``FocalContext.doSomething`` as produced on
#: tree-sitter / tree-sitter-java 0.23.2 (see note 1 in the module docstring).
DO_SOMETHING_PARAMETERS = (
    "doSomething(Map.Entry<String,@NullableString>, List<ExternalContext01>, "
    "ExternalContext01, Map.Entry<String,ExternalContext01>, Object[])"
)

#: ``parameters`` of the first ``runSomeVoid`` overload
#: ([`FocalContext.java:83`](tests/fixtures/java/sample_java_repo/src/main/com/eljavatar/focals/FocalContext.java:83)).
RUN_SOME_VOID_STRING_PARAMETERS = "runSomeVoid(String)"

#: Keys removed in place by the name strategy
#: ([`find_map_tests_cases_from_repo.py:617-618`](find_map_tests_cases_from_repo.py:617))
#: and by the single-invocation strategy
#: ([`find_map_tests_cases_from_repo.py:655-656`](find_map_tests_cases_from_repo.py:655)).
DEPENDENCY_KEYS_REMOVED_ON_MATCH = (
    "method_dependencies_by_class",
    "method_references_dependencies_by_class",
)

#: The four test cases the heuristics map in a single full pass
#: (``TEST_PLAN.md`` section B.4 summary).
MAPPED_TEST_CASE_NAMES = [
    "testDoSomething",
    "DoSomethingTest",
    "verifyBehaviour",
    "runSomeVoidTest",
]


def _test_case(test_cases: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
    """Return the single parsed test case called ``name``."""
    matches = [test_case for test_case in test_cases if test_case["method_name"] == name]
    assert len(matches) == 1, f"expected exactly one test case named {name!r}, got {len(matches)}"
    return matches[0]


def _match(
    fm_repo_module,
    parserutils,
    inputs: Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]],
    test_case_name: str | None = None,
):
    """Run ``match_test_cases()`` over one test case (or all of them) and return ``(mapped, log)``."""
    test_class, focal_class, test_cases, focal_methods = inputs
    if test_case_name is None:
        selected = test_cases
    else:
        selected = [_test_case(test_cases, test_case_name)]

    log = io.StringIO()
    mapped = fm_repo_module.match_test_cases(
        parserutils, test_class, focal_class, selected, focal_methods, log
    )
    return mapped, log


# ---------------------------------------------------------------------------
# Strategy 1 — name matching
# ---------------------------------------------------------------------------
def test_u_map_01_name_match_maps_test_do_something(fm_repo_module, dependency_parser_utils, match_inputs_real):
    """U-MAP-01: ``testDoSomething`` -> ``doSomething`` by normalised name."""
    mapped, _log = _match(
        fm_repo_module, dependency_parser_utils, match_inputs_real, "testDoSomething"
    )

    assert len(mapped) == 1
    assert mapped[0]["focal_method"]["method_name"] == "doSomething"
    # Observed on 0.23.2 (not the plan's 'int val'; see module docstring note 1).
    assert mapped[0]["focal_method"]["parameters"] == DO_SOMETHING_PARAMETERS
    assert len(mapped[0]["focal_method"]["parameters_list"]) == 5
    assert "method_dependencies_by_class" not in mapped[0]["test_case"]


def test_u_map_02_trailing_test_suffix_is_stripped(fm_repo_module, dependency_parser_utils, match_inputs_real):
    """U-MAP-02: ``DoSomethingTest`` -> ``dosomething`` after the ``test`` suffix is cut."""
    mapped, _log = _match(
        fm_repo_module, dependency_parser_utils, match_inputs_real, "DoSomethingTest"
    )

    assert len(mapped) == 1
    assert mapped[0]["focal_method"]["method_name"] == "doSomething"
    assert mapped[0]["test_case"]["method_name"] == "DoSomethingTest"


# ---------------------------------------------------------------------------
# Strategy 2 — single invocation
# ---------------------------------------------------------------------------
def test_u_map_03_single_focal_invocation_is_mapped(fm_repo_module, dependency_parser_utils, match_inputs_real):
    """U-MAP-03: one invocation on the focal class resolves to that focal method."""
    mapped, log = _match(
        fm_repo_module, dependency_parser_utils, match_inputs_real, "verifyBehaviour"
    )

    assert len(mapped) == 1
    # Observed on 0.23.2 (not the plan's 'String val'; see module docstring note 1).
    assert mapped[0]["focal_method"]["parameters"] == RUN_SOME_VOID_STRING_PARAMETERS
    assert mapped[0]["focal_method"]["parameters_list"] == ["String"]
    assert mapped[0]["focal_method"]["method_name"] == "runSomeVoid"
    assert "> [Single-Invocation] Found Focal-Method:" in log.getvalue()


def test_u_map_04_two_focal_invocations_are_rejected_as_ambiguous(
    fm_repo_module, dependency_parser_utils, match_inputs_real
):
    """U-MAP-04: two dependencies on the focal class -> ``continue``, nothing mapped."""
    test_class, focal_class, test_cases, focal_methods = match_inputs_real
    test_case = _test_case(test_cases, "verifyAmbiguous")
    assert sorted(test_case["method_dependencies_by_class"]["FocalContext"]) == [
        "callSomeMethod(int)",
        "runSomeVoid(String)",
    ]

    mapped, log = _match(
        fm_repo_module, dependency_parser_utils, match_inputs_real, "verifyAmbiguous"
    )

    assert mapped == []
    assert "Test-Case: verifyAmbiguous" in log.getvalue()
    assert "[Single-Invocation]" not in log.getvalue()


def test_u_map_05_no_focal_invocation_stays_unmapped(fm_repo_module, dependency_parser_utils, match_inputs_real):
    """U-MAP-05: no call into the focal class -> empty extraction -> nothing mapped."""
    mapped, log = _match(
        fm_repo_module, dependency_parser_utils, match_inputs_real, "verifyNoInvocation"
    )

    assert mapped == []
    assert "Test-Case: verifyNoInvocation" in log.getvalue()
    assert "[Single-Invocation]" not in log.getvalue()


@pytest.mark.regression
def test_u_map_06_overloaded_name_match_always_picks_first_declaration(
    fm_repo_module, dependency_parser_utils, match_inputs_real
):
    """U-MAP-06: regression lock for the overload-insensitive ``list.index()``.

    ``runSomeVoidTest`` invokes ``runSomeVoid(1L)`` (``long``) but name matching
    keeps only ``focal_methods_names_norm`` and takes the *first* hit via
    ``list.index()`` ([`find_map_tests_cases_from_repo.py:614`](find_map_tests_cases_from_repo.py:614)),
    which is the ``String`` overload declared at
    [`FocalContext.java:83`](tests/fixtures/java/sample_java_repo/src/main/com/eljavatar/focals/FocalContext.java:83).
    """
    _test_class, _focal_class, test_cases, _focal_methods = match_inputs_real
    test_case = _test_case(test_cases, "runSomeVoidTest")
    # The real invocation's resolved type is ``long``, not ``String``.
    assert list(test_case["method_dependencies_by_class"]["FocalContext"]) == ["runSomeVoid(long)"]

    mapped, log = _match(
        fm_repo_module, dependency_parser_utils, match_inputs_real, "runSomeVoidTest"
    )

    assert len(mapped) == 1
    assert mapped[0]["focal_method"]["parameters"] == RUN_SOME_VOID_STRING_PARAMETERS
    assert mapped[0]["focal_method"]["parameters_list"] == ["String"]
    # Name strategy, not the invocation strategy.
    assert "> Found Focal-Method: runSomeVoid(String)" in log.getvalue()
    assert "[Single-Invocation]" not in log.getvalue()


@pytest.mark.xfail(strict=True, reason="desired behaviour after the Spoon migration (TEST_PLAN U-MAP-07)")
@pytest.mark.xfail_spoon
def test_u_map_07_overload_resolution_should_use_arity_and_type(
    fm_repo_module, dependency_parser_utils, match_inputs_real
):
    """U-MAP-07 (desired): ``runSomeVoidTest`` should map to the ``Long`` overload.

    Asserted through ``parameters_list`` rather than the plan's ``'Long val'``
    string, so the expected behaviour does not depend on the ``parameters``
    textual format pinned in U-MAP-01/U-MAP-03/U-MAP-06.
    """
    mapped, _log = _match(
        fm_repo_module, dependency_parser_utils, match_inputs_real, "runSomeVoidTest"
    )

    assert len(mapped) == 1
    assert mapped[0]["focal_method"]["parameters_list"] == ["Long"]


# ---------------------------------------------------------------------------
# Strategy 3 — dependencies belonging to another class
# ---------------------------------------------------------------------------
def test_u_map_08_dependency_of_other_class_is_rejected(fm_repo_module, dependency_parser_utils, match_inputs_real):
    """U-MAP-08: only ``SamePackageExternal01`` is invoked -> no focal match."""
    _test_class, _focal_class, test_cases, _focal_methods = match_inputs_real
    test_case = _test_case(test_cases, "verifyOtherClass")
    assert list(test_case["method_dependencies_by_class"]) == ["SamePackageExternal01"]

    mapped, log = _match(
        fm_repo_module, dependency_parser_utils, match_inputs_real, "verifyOtherClass"
    )

    assert mapped == []
    assert "Test-Case: verifyOtherClass" in log.getvalue()
    assert "[Single-Invocation]" not in log.getvalue()


# ---------------------------------------------------------------------------
# Mutation contract and metrics
# ---------------------------------------------------------------------------
def test_u_map_09_matched_test_case_is_mutated_in_place(fm_repo_module, dependency_parser_utils, match_inputs_real):
    """U-MAP-09: exactly one matched test case, mutated and re-used by identity."""
    test_class, focal_class, test_cases, focal_methods = match_inputs_real
    test_case = _test_case(test_cases, "testDoSomething")
    for key in DEPENDENCY_KEYS_REMOVED_ON_MATCH:
        assert key in test_case

    log = io.StringIO()
    mapped = fm_repo_module.match_test_cases(
        dependency_parser_utils, test_class, focal_class, [test_case], focal_methods, log
    )

    assert len(mapped) == 1
    assert mapped[0]["test_case"] is test_case
    assert mapped[0]["test_case"]["method_name"] == "testDoSomething"
    for key in DEPENDENCY_KEYS_REMOVED_ON_MATCH:
        assert key not in test_case


def test_u_map_10_log_reports_global_metrics(fm_repo_module, dependency_parser_utils, match_inputs_real):
    """U-MAP-10: a full pass over the seven ``@Test`` methods logs the aggregate metrics."""
    _test_class, _focal_class, test_cases, _focal_methods = match_inputs_real
    assert len(test_cases) == 7

    mapped, log = _match(fm_repo_module, dependency_parser_utils, match_inputs_real)
    contents = log.getvalue()

    assert len(mapped) == 4
    assert [entry["test_case"]["method_name"] for entry in mapped] == MAPPED_TEST_CASE_NAMES
    assert "+++++++++" in contents
    assert "Test-Cases: 7" in contents
    assert "Mapped Test Cases: 4" in contents
    # Observed extras of the same block
    # ([`find_map_tests_cases_from_repo.py:671-675`](find_map_tests_cases_from_repo.py:671)).
    assert "Focal Methods: 12" in contents
    assert "Tested Focal Methods: 2" in contents
