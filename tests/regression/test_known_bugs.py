"""Regression locks for known (deliberately unfixed) defects.

TEST_PLAN section A assigns four ids to this file: U-AST-09, U-DUP-03,
U-CLI-01 and U-MAP-06.  They pin *current* production behaviour that is known to
be imperfect, so that an accidental "fix" changes the corpus silently no more:
the new behaviour trips the lock instead, and the fix has to update the plan and
the test on purpose.

Intentional duplication (read before editing)
---------------------------------------------
The same ids are pinned by the unit suite:

* U-AST-09 — [`tests/unit/test_class_parser.py`](tests/unit/test_class_parser.py:191)
* U-DUP-03 — [`tests/unit/test_clean_duplicates.py`](tests/unit/test_clean_duplicates.py:152)
* U-CLI-01 — [`tests/unit/test_cli_args.py`](tests/unit/test_cli_args.py:61)
* U-MAP-06 — [`tests/unit/test_match_test_cases.py`](tests/unit/test_match_test_cases.py:203)

To make the duplication useful (a future production change must trip at least one
of the two files) every assertion here is re-expressed with *independent* inputs:

* U-AST-09 uses a different, nested non-existent path and additionally pins the
  ``FileNotFoundError.filename`` attribute, not only the exception type.
* U-DUP-03 puts ``None`` on the **focal** body (``method_src_code``) instead of
  the test body, i.e. it exercises the *other* operand of the concatenation at
  [`clean_duplicates_and_build_dataset.py:103`](clean_duplicates_and_build_dataset.py:103).
* U-CLI-01 uses values that ``bool()`` also accepts (``"no"``, ``"0"``,
  ``"off"``, a single space) instead of ``"False"``.
* U-MAP-06 uses hand-written ``focal_methods`` / ``test_cases`` dictionaries
  instead of the real ``FocalContext`` Java fixture, so the lock does not depend
  on tree-sitter parsing at all (only on the ``list.index()`` heuristic).

Nothing outside ``tmp_path`` is written, no fixture is added to
``tests/conftest.py`` and no production file is modified.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

pytestmark = [pytest.mark.regression]

#: Class name used by the hand-written U-MAP-06 fixture (unrelated to
#: ``FocalContext`` on purpose: the lock must not depend on the Java tree).
HAND_WRITTEN_FOCAL_CLASS = "RegressionLockFocal"


# ---------------------------------------------------------------------------
# Local helpers (module-private; not fixtures)
# ---------------------------------------------------------------------------
def _write_mining_records(path_in: Path, repo_id: str, records: Dict[str, Dict[str, Any]]) -> Path:
    """Create ``path_in/<repo_id>/<name>.json`` for each ``records`` entry."""
    repo_dir = path_in / repo_id
    repo_dir.mkdir(parents=True, exist_ok=True)
    for file_name, record in records.items():
        (repo_dir / file_name).write_text(json.dumps(record), encoding="utf-8")
    return repo_dir


def _overload(parameter_type: str) -> Dict[str, Any]:
    """A minimal ``focal_method`` dict accepted by ``match_test_cases()``."""
    return {
        "method_name": "compute",
        "parameters": f"compute({parameter_type})",
        "parameters_list": [parameter_type],
        "class": {"class_name": HAND_WRITTEN_FOCAL_CLASS},
    }


def _named_test_case(invoked_signature: str) -> Dict[str, Any]:
    """A minimal ``test_case`` dict whose name matches the ``compute`` overloads.

    ``computeTest`` is normalised to ``compute`` by the trailing-``test`` rule at
    [`find_map_tests_cases_from_repo.py:604`](find_map_tests_cases_from_repo.py:604).
    """
    return {
        "method_name": "computeTest",
        "method_dependencies_by_class": {HAND_WRITTEN_FOCAL_CLASS: [invoked_signature]},
        "method_references_dependencies_by_class": {},
    }


# ---------------------------------------------------------------------------
# U-AST-09 -- obstacle O6: open() outside the try block propagates the error
# ---------------------------------------------------------------------------
def test_u_ast_09_regression_missing_path_propagates_file_not_found(class_parser, tmp_path):
    """U-AST-09: ``parse_file()`` never returns ``[]`` for a missing path.

    The ``open()`` of [`ClassParser.py:41`](ClassParser.py:41) sits outside the
    ``try`` block, so the ``FileNotFoundError`` escapes.  The nested directory
    (different from the unit lock) also proves the error comes from the target
    file and not from a directory-missing special case.
    """
    missing = tmp_path / "regression_inputs" / "src" / "main" / "AbsentFocal.java"
    assert not missing.exists()
    assert not missing.parent.exists()

    with pytest.raises(FileNotFoundError) as exc_info:
        class_parser.parse_file(str(missing))

    # Pinned finer than "raises": the exception points at the requested path.
    assert exc_info.value.filename == str(missing)


# ---------------------------------------------------------------------------
# U-DUP-03 -- obstacle O7: concatenation happens before the None guard
# ---------------------------------------------------------------------------
def test_u_dup_03_regression_none_focal_body_aborts_before_none_guard(
    clean_duplicates_module, make_mtc_json, tmp_path
):
    """U-DUP-03: a ``None`` *focal* body raises ``TypeError``, it is not skipped.

    ``method_src_code + test_src_code`` at
    [`clean_duplicates_and_build_dataset.py:103`](clean_duplicates_and_build_dataset.py:103)
    is evaluated before the ``method_src_code is None`` branch of the guard at
    [`clean_duplicates_and_build_dataset.py:115`](clean_duplicates_and_build_dataset.py:115),
    so the record aborts the whole run instead of being discarded.
    """
    path_in = tmp_path / "regression_mining" / "train" / "output"
    record = make_mtc_json(body_focal='public String helper(int val) { return "x"; }')
    record["focal_method"]["body"] = None
    repo_dir = _write_mining_records(path_in, "regression_repo", {"none_focal.json": record})
    assert (repo_dir / "none_focal.json").is_file()

    path_out = tmp_path / "regression_dataset" / "train"

    # ``None + str`` raises before the intended filter is reached.
    with pytest.raises(TypeError, match="NoneType"):
        clean_duplicates_module.extract_uniques(
            "train", set(), set(), str(path_in), str(path_out)
        )

    # The output folder is created only after the filter
    # (clean_duplicates_and_build_dataset.py:128), so the abort leaves no trace.
    assert not (path_out / "regression_repo").exists()


# ---------------------------------------------------------------------------
# U-CLI-01 -- obstacle O4: argparse ``type=bool`` on a string option
# ---------------------------------------------------------------------------
def test_u_cli_01_regression_type_bool_coerces_any_non_empty_string(
    monkeypatch, build_corpus_module
):
    """U-CLI-01: ``type=bool`` ([`build_corpus.py:744`](build_corpus.py:744)).

    ``argparse`` applies the ``bool`` constructor to the raw string, so every
    non-empty value is truthy -- including the strings a user would write to
    *disable* the option.  Only ``""`` is falsy.
    """
    for raw_value in ("false", "False", "FALSE", "0", "no", "off", " "):
        monkeypatch.setattr(
            sys, "argv", ["prog", "--validate_against_d4j_dataset", raw_value]
        )
        parsed = build_corpus_module.parse_args()["validate_against_d4j_dataset"]
        assert parsed is True, f"type=bool should coerce {raw_value!r} to True"
        assert isinstance(parsed, bool)

    monkeypatch.setattr(sys, "argv", ["prog", "--validate_against_d4j_dataset", ""])
    assert build_corpus_module.parse_args()["validate_against_d4j_dataset"] is False


# ---------------------------------------------------------------------------
# U-MAP-06 -- obstacle O3: overload-insensitive list.index()
# ---------------------------------------------------------------------------
def test_u_map_06_regression_overloaded_names_pick_first_declaration(
    fm_repo_module, dependency_parser_utils, tmp_log
):
    """U-MAP-06: name matching always resolves to the first declaration.

    ``match_test_cases()`` compares only normalised *names* and takes the first
    hit with ``list.index()``
    ([`find_map_tests_cases_from_repo.py:614`](find_map_tests_cases_from_repo.py:614)),
    even though the test case records that it invokes ``compute(long)``.
    """
    focal_methods: List[Dict[str, Any]] = [_overload("String"), _overload("long")]
    test_case = _named_test_case("compute(long)")
    assert test_case["method_dependencies_by_class"] == {
        HAND_WRITTEN_FOCAL_CLASS: ["compute(long)"]
    }

    mapped = fm_repo_module.match_test_cases(
        dependency_parser_utils,
        {"class_name": f"{HAND_WRITTEN_FOCAL_CLASS}Test"},
        {"class_name": HAND_WRITTEN_FOCAL_CLASS},
        [test_case],
        focal_methods,
        tmp_log,
    )

    assert len(mapped) == 1
    # Identity, not equality: the *first* declaration object wins.
    assert mapped[0]["focal_method"] is focal_methods[0]
    assert mapped[0]["focal_method"]["parameters_list"] == ["String"]
    assert "Found Focal-Method: compute(String)" in tmp_log.getvalue()
    # The invocation recorded by the test case disagreed with the resolution,
    # and both dependency keys are consumed in place (mutation contract).
    assert "method_dependencies_by_class" not in test_case
    assert "method_references_dependencies_by_class" not in test_case
