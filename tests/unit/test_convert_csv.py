"""Unit tests for ``convert_json_corpus_to_csv_input.py`` (TEST_PLAN B.7, U-CSV-01..U-CSV-06).

Targets
-------
* [`convert()`](convert_json_corpus_to_csv_input.py:25)
* the module-level ``SEED`` constant
  ([`convert_json_corpus_to_csv_input.py:8`](convert_json_corpus_to_csv_input.py:8))

The module is never imported at test-module level: it is obtained through the
``convert_csv_module`` fixture, which loads it under the stable alias
``dynamtests_convert_csv`` (obstacle O2).  ``main()`` is never called, because its
defaults point at hard-coded ``E:/000_Tesis/project_tesis_build_dataset/...``
paths ([`convert_json_corpus_to_csv_input.py:131-155`](convert_json_corpus_to_csv_input.py:131)).

Pinned production facts
-----------------------
* ``convert()`` takes no encoding parameter and the writer hard-codes
  ``encoding="utf-8"`` at
  [`convert_json_corpus_to_csv_input.py:114`](convert_json_corpus_to_csv_input.py:114);
  the assertions therefore compare *Python-side* values after the CSV round trip,
  never byte-level encodings.
* ``df.sample(frac=1, random_state=SEED).reset_index(drop=True)`` at
  [`convert_json_corpus_to_csv_input.py:110`](convert_json_corpus_to_csv_input.py:110)
  makes the written row order deterministic; ``SEED`` is pinned to ``42``.
* The input path is assembled as ``str(path) + '/' + name`` at
  [`convert_json_corpus_to_csv_input.py:38`](convert_json_corpus_to_csv_input.py:38)
  (mixed separators); valid on Windows and POSIX, so tests do not normalise it.
* Every column of the corpus record is a string, so ``pandas`` keeps them all as
  ``object`` after ``to_csv`` / ``read_csv``; no dtype coercion is asserted beyond
  the explicit ``dtype=str`` read used where the plan demands a value comparison.

Documented divergence -- U-CSV-06
---------------------------------
``TEST_PLAN`` U-CSV-06 expects an empty corpus to produce a CSV file whose
``pd.read_csv`` raises ``pandas.errors.EmptyDataError``.  The observed behaviour is
different: with no JSON files ``pd.DataFrame([])`` has zero columns, so the debug
print at
[`convert_json_corpus_to_csv_input.py:91`](convert_json_corpus_to_csv_input.py:91)
raises ``IndexError: single positional indexer is out-of-bounds`` and the CSV file
is never written (only the output directory created at
[`convert_json_corpus_to_csv_input.py:26`](convert_json_corpus_to_csv_input.py:26)
exists).  The test pins the observed behaviour instead of the planned one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd
import pytest

pytestmark = pytest.mark.unit

#: Column order emitted by ``convert()`` (same order as the JSON record keys).
CSV_COLUMNS = [
    "target",
    "src_fm_fc_ms_ff",
    "src_fm_fc_dctx",
    "src_fm_fc_dctx_priv",
    "imports_focal_class",
    "imports_test_class",
]


# ---------------------------------------------------------------------------
# Local helpers (module-private, no conftest fixture is added)
# ---------------------------------------------------------------------------
def _out_csv(out_dir: Path, type_corpus: str = "validation") -> Path:
    """``<out_dir>/<type_corpus>.csv``, the name built at line 27."""
    return out_dir / f"{type_corpus}.csv"


def _write_corpus(split_dir: Path, records_by_repo: Dict[str, Iterable[Dict[str, Any]]]) -> None:
    """Materialise ``<split_dir>/<repo>/<repo>_<i>_corpus.json`` for every record."""
    for repo_id, records in records_by_repo.items():
        repo_dir = split_dir / repo_id
        repo_dir.mkdir(parents=True, exist_ok=True)
        for index, record in enumerate(records):
            (repo_dir / f"{repo_id}_{index}_corpus.json").write_text(
                json.dumps(record, ensure_ascii=False), encoding="utf-8"
            )


# ---------------------------------------------------------------------------
# U-CSV-01 .. U-CSV-05 -- happy path over the shared 2-repo JSON corpus
# ---------------------------------------------------------------------------
def test_u_csv_01_header_is_the_six_corpus_columns(
    convert_csv_module, json_corpus_2_repos: Path, tmp_path: Path
) -> None:
    """U-CSV-01: the CSV header is exactly the six stage-3 corpus columns."""
    out_dir = tmp_path / "csv_out"

    convert_csv_module.convert("validation", str(json_corpus_2_repos), str(out_dir))

    csv_path = _out_csv(out_dir)
    assert csv_path.is_file()
    header = pd.read_csv(csv_path, nrows=0)
    assert header.columns.tolist() == CSV_COLUMNS


def test_u_csv_02_two_records_become_two_rows(
    convert_csv_module, json_corpus_2_repos: Path, tmp_path: Path
) -> None:
    """U-CSV-02: one CSV row per JSON record (2 repos -> 2 rows)."""
    out_dir = tmp_path / "csv_out"

    convert_csv_module.convert("validation", str(json_corpus_2_repos), str(out_dir))

    df = pd.read_csv(_out_csv(out_dir), dtype=str)
    assert len(df) == 2
    assert df["target"].notna().all()


def test_u_csv_03_target_round_trips_newlines_commas_and_quotes(
    convert_csv_module, make_corpus_record, tmp_path: Path
) -> None:
    """U-CSV-03: quoting round-trips a ``target`` holding ``\\n``, ``,`` and ``"``.

    Uses a single-record corpus so the shuffled frame has exactly one row and
    ``df.loc[0, 'target']`` is unambiguous after ``reset_index``.
    """
    original = 'public void testCase0() {\n\tAssert.assertEquals("a,b", "c");\n}'
    record = make_corpus_record(0)
    record["target"] = original

    split_dir = tmp_path / "corpus" / "json" / "validation"
    _write_corpus(split_dir, {"repoA": [record]})
    out_dir = tmp_path / "csv_out"

    convert_csv_module.convert("validation", str(split_dir), str(out_dir))

    df = pd.read_csv(_out_csv(out_dir))
    assert len(df) == 1
    assert df.loc[0, "target"] == original


def test_u_csv_04_seed_42_makes_output_byte_identical_across_runs(
    convert_csv_module, json_corpus_2_repos: Path, tmp_path: Path
) -> None:
    """U-CSV-04: ``SEED == 42`` and two conversions of the same input are identical."""
    assert convert_csv_module.SEED == 42

    first = tmp_path / "csv_run_1"
    second = tmp_path / "csv_run_2"

    convert_csv_module.convert("validation", str(json_corpus_2_repos), str(first))
    convert_csv_module.convert("validation", str(json_corpus_2_repos), str(second))

    assert _out_csv(first).read_bytes() == _out_csv(second).read_bytes()


def test_u_csv_05_output_file_named_after_type_corpus(
    convert_csv_module, json_corpus_2_repos: Path, tmp_path: Path
) -> None:
    """U-CSV-05: the output file name is ``<type_corpus>.csv`` (line 27)."""
    out_dir = tmp_path / "csv_out"

    convert_csv_module.convert("validation", str(json_corpus_2_repos), str(out_dir))

    assert (out_dir / "validation.csv").is_file()
    assert [path.name for path in out_dir.iterdir()] == ["validation.csv"]


# ---------------------------------------------------------------------------
# U-CSV-06 -- empty corpus (documented divergence, see module docstring)
# ---------------------------------------------------------------------------
def test_u_csv_06_empty_corpus_raises_index_error_before_writing(
    convert_csv_module, tmp_path: Path
) -> None:
    """U-CSV-06: no JSON files -> ``IndexError`` at line 91, no CSV written.

    Observed behaviour (pinned): the debug print ``df.iloc[:1, 0]`` on a
    zero-column frame raises ``IndexError`` before ``to_csv``, so the output
    directory exists but ``validation.csv`` does not.
    """
    split_dir = tmp_path / "corpus" / "json" / "validation"
    (split_dir / "repoEmpty").mkdir(parents=True)
    out_dir = tmp_path / "csv_out"

    with pytest.raises(IndexError, match="single positional indexer is out-of-bounds"):
        convert_csv_module.convert("validation", str(split_dir), str(out_dir))

    assert out_dir.is_dir()
    assert not (out_dir / "validation.csv").exists()
