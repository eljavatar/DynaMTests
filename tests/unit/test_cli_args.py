"""Unit tests for the two ``parse_args()`` entry points (TEST_PLAN section B.7, U-CLI-01..U-CLI-04).

Targets
-------
* [`build_corpus.parse_args()`](build_corpus.py:716) — U-CLI-01, U-CLI-02, U-CLI-03
* [`find_map_tests_cases_from_repo.parse_args()`](find_map_tests_cases_from_repo.py:798) — U-CLI-04

``parse_args()`` is called only after ``monkeypatch.setattr(sys, "argv", [...])``;
``main()`` is never invoked, so no filesystem or network side effect can occur.
Both modules are obtained through the ``build_corpus_module`` / ``fm_repo_module``
fixtures (``find_map_tests_cases_from_repo.py`` reads ``os.environ`` at import
time — [`find_map_tests_cases_from_repo.py:32-33`](find_map_tests_cases_from_repo.py:32)).

Pinned bug (TEST_PLAN obstacle O4)
----------------------------------
``--validate_against_d4j_dataset`` is declared with ``type=bool``
([`build_corpus.py:742-747`](build_corpus.py:742)), so ``argparse`` applies the
Python constructor ``bool`` to the *raw string*. Consequently **any non-empty
string is truthy**: ``"--validate_against_d4j_dataset False"`` yields ``True``.
Only the empty string yields ``False``. U-CLI-01 pins these real semantics
(the ``args is True`` assertion of the plan); the idealised behaviour belongs to
``tests/regression/test_spoon_desired.py`` (U-CLI-02) and is **out of scope**
for this file.

No fixture is added to ``conftest.py``; nothing is written to disk and no
``.rooignore``d path is read.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.unit

#: Keys returned by [`build_corpus.parse_args()`](build_corpus.py:716) on 0.23.2.
BUILD_CORPUS_ARG_KEYS = {
    "d4j_dataset",
    "input_dataset",
    "input_encoding",
    "output_corpus",
    "tag_external_context_end",
    "tag_external_context_start",
    "tag_focal_context_end",
    "tag_focal_context_start",
    "tag_private_focal_context_end",
    "tag_private_focal_context_start",
    "type_dataset",
    "validate_against_d4j_dataset",
}

#: Keys returned by
#: [`find_map_tests_cases_from_repo.parse_args()`](find_map_tests_cases_from_repo.py:798).
FIND_MAP_ARG_KEYS = {"output", "output_empty", "repo_id", "repo_url", "repos_file", "tmp"}


# ---------------------------------------------------------------------------
# build_corpus.py
# ---------------------------------------------------------------------------
def test_u_cli_01_bool_flag_parsing_keeps_the_type_bool_bug(monkeypatch, build_corpus_module):
    """U-CLI-01: ``type=bool`` turns the string ``"False"`` into ``True``."""
    monkeypatch.setattr(sys, "argv", ["prog", "--validate_against_d4j_dataset", "False"])
    args = build_corpus_module.parse_args()
    assert args["validate_against_d4j_dataset"] is True

    # Same defect, shown from the other side: only an empty string is falsy.
    monkeypatch.setattr(sys, "argv", ["prog", "--validate_against_d4j_dataset", ""])
    assert build_corpus_module.parse_args()["validate_against_d4j_dataset"] is False

    # Default declared at [`build_corpus.py:745`](build_corpus.py:745).
    monkeypatch.setattr(sys, "argv", ["prog"])
    assert build_corpus_module.parse_args()["validate_against_d4j_dataset"] is True


def test_u_cli_03_build_corpus_defaults(monkeypatch, build_corpus_module):
    """U-CLI-03: default tag literals, encoding and dataset type."""
    monkeypatch.setattr(sys, "argv", ["prog"])
    args = build_corpus_module.parse_args()

    assert set(args) == BUILD_CORPUS_ARG_KEYS
    assert args["tag_focal_context_start"] == "<FCTX>"
    assert args["tag_focal_context_end"] == "</FCTX>"
    assert args["tag_external_context_start"] == "<ECTX>"
    assert args["tag_external_context_end"] == "</ECTX>"
    assert args["tag_private_focal_context_start"] == "<PRIVATE_FCTX>"
    assert args["tag_private_focal_context_end"] == "</PRIVATE_FCTX>"
    assert args["input_encoding"] == "utf-8"
    assert args["type_dataset"] == "train"


# ---------------------------------------------------------------------------
# find_map_tests_cases_from_repo.py
# ---------------------------------------------------------------------------
def test_u_cli_04_find_map_defaults(monkeypatch, fm_repo_module):
    """U-CLI-04: ``repo_url`` / ``repo_id`` defaults and the absent ``repos_file``."""
    monkeypatch.setattr(sys, "argv", ["prog"])
    args = fm_repo_module.parse_args()

    assert set(args) == FIND_MAP_ARG_KEYS
    assert args["repo_url"] == "https://github.com/google/gson"
    assert args["repo_id"] == "32538871"
    assert args["repos_file"] is None
