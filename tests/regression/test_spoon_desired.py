"""Spoon-alignment / desired behaviour contracts (strict ``xfail``).

TEST_PLAN section A assigns three ids to this file: U-MAP-07, U-DUP-04 and
U-CLI-02.  All three describe behaviour the pipeline **does not** have today and
**must** have after the Spoon migration; they are the only ``xfail``s of the
suite, so a green pipeline is distinguished from a broken test.

Marker convention (copied from the existing strict xfails in
[`tests/unit/test_match_test_cases.py`](tests/unit/test_match_test_cases.py:231)
and [`tests/unit/test_clean_duplicates.py`](tests/unit/test_clean_duplicates.py:178)):

* ``pytestmark`` adds the module-wide ``regression`` and ``xfail_spoon`` tags;
* every test carries ``@pytest.mark.xfail(strict=True, reason="Spoon-desired: ...")``.

A bare ``xfail_spoon`` tag alone would report ``FAILED``; ``strict=True`` reports
``XFAIL`` today and turns into ``FAILED`` (``XPASS``) as soon as production is
fixed -- that is the signal to delete the test and remove the corresponding row
from the plan.

Relation to the unit suite
--------------------------
The current-behaviour counterparts live in
[`tests/unit/test_match_test_cases.py`](tests/unit/test_match_test_cases.py:203),
[`tests/unit/test_clean_duplicates.py`](tests/unit/test_clean_duplicates.py:152)
and [`tests/unit/test_cli_args.py`](tests/unit/test_cli_args.py:61).  The
assertions below intentionally use *different* inputs so a half-fix is caught
twice:

* U-MAP-07 — hand-written ``focal_methods`` / ``test_cases`` dicts (no
  tree-sitter), so the desired arity/type contract is expressed independently of
  the ``FocalContext`` Java fixture.
* U-DUP-04 — two records (one ``None`` test body plus one valid record), so the
  desired contract is "skip the broken record **and keep the good one**", not
  merely "do not crash".
* U-CLI-02 — lower-case spellings in addition to the plan's ``"False"``.

Hermetic: everything is written below ``tmp_path``; no network, no fixture added
to ``tests/conftest.py``, no production file touched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

pytestmark = [pytest.mark.regression, pytest.mark.xfail_spoon]

#: Class name used by the hand-written U-MAP-07 fixture.
HAND_WRITTEN_FOCAL_CLASS = "SpoonDesiredFocal"


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
    """A minimal ``test_case`` dict whose name matches the ``compute`` overloads."""
    return {
        "method_name": "computeTest",
        "method_dependencies_by_class": {HAND_WRITTEN_FOCAL_CLASS: [invoked_signature]},
        "method_references_dependencies_by_class": {},
    }


# ---------------------------------------------------------------------------
# U-MAP-07 -- desired: overload resolution by arity and parameter type
# ---------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="Spoon-desired: arity/type-aware overload resolution (TEST_PLAN U-MAP-07)")
def test_u_map_07_desired_arity_type_aware_overload_resolution(
    fm_repo_module, dependency_parser_utils, tmp_log
):
    """U-MAP-07 (desired): the invoked ``compute(long)`` resolves to the ``long`` overload.

    Today [`find_map_tests_cases_from_repo.py:614`](find_map_tests_cases_from_repo.py:614)
    takes the first declaration by name, which is ``compute(String)`` here.
    """
    focal_methods: List[Dict[str, Any]] = [_overload("String"), _overload("long")]
    test_case = _named_test_case("compute(long)")

    mapped = fm_repo_module.match_test_cases(
        dependency_parser_utils,
        {"class_name": f"{HAND_WRITTEN_FOCAL_CLASS}Test"},
        {"class_name": HAND_WRITTEN_FOCAL_CLASS},
        [test_case],
        focal_methods,
        tmp_log,
    )

    assert len(mapped) == 1
    # Desired contract: the resolution agrees with the recorded invocation.
    assert mapped[0]["focal_method"]["parameters_list"] == ["long"]


# ---------------------------------------------------------------------------
# U-DUP-04 -- desired: skip the None record, keep processing the rest
# ---------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="Spoon-desired: skip records with a None body instead of aborting (TEST_PLAN U-DUP-04)")
def test_u_dup_04_desired_skip_none_body_and_keep_valid_record(
    clean_duplicates_module, make_mtc_json, tmp_path
):
    """U-DUP-04 (desired): a ``None`` test body is filtered, not concatenated.

    The intended guard already exists at
    [`clean_duplicates_and_build_dataset.py:115`](clean_duplicates_and_build_dataset.py:115);
    it only has to be evaluated before the concatenation at
    [`clean_duplicates_and_build_dataset.py:103`](clean_duplicates_and_build_dataset.py:103).
    """
    path_in = tmp_path / "spoon_mining" / "validation" / "output"

    broken = make_mtc_json(body_test="public void testBrokenBody() { }")
    broken["test_case"]["body"] = None
    valid = make_mtc_json(
        body_test="public void testValidBody() { Assert.assertTrue(true); }",
        test_case_name="testValidBody",
    )
    _write_mining_records(
        path_in, "spoon_repo", {"broken_body.json": broken, "valid_body.json": valid}
    )

    path_out = tmp_path / "spoon_dataset" / "validation"
    accepted, ignored = clean_duplicates_module.extract_uniques(
        "validation", set(), set(), str(path_in), str(path_out)
    )

    # One record is discarded for the None body, the other one is accepted.
    assert (accepted, ignored) == (1, 1)
    copied = sorted(path.name for path in (path_out / "spoon_repo").iterdir())
    assert copied == ["valid_body.json"]


# ---------------------------------------------------------------------------
# U-CLI-02 -- desired: a real boolean flag
# ---------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="Spoon-desired: strict boolean parsing instead of type=bool (TEST_PLAN U-CLI-02)")
def test_u_cli_02_desired_strict_boolean_flag_parsing(monkeypatch, build_corpus_module):
    """U-CLI-02 (desired): ``--validate_against_d4j_dataset False`` means ``False``.

    ``type=bool`` ([`build_corpus.py:744`](build_corpus.py:744)) coerces the raw
    string, so the current answer is ``True`` for every spelling below.
    """
    for raw_value in ("False", "false"):
        monkeypatch.setattr(
            sys, "argv", ["prog", "--validate_against_d4j_dataset", raw_value]
        )
        assert build_corpus_module.parse_args()["validate_against_d4j_dataset"] is False, raw_value

    for raw_value in ("True", "true"):
        monkeypatch.setattr(
            sys, "argv", ["prog", "--validate_against_d4j_dataset", raw_value]
        )
        assert build_corpus_module.parse_args()["validate_against_d4j_dataset"] is True, raw_value
