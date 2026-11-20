"""Unit tests for ``clean_duplicates_and_build_dataset.py`` (TEST_PLAN B.6, U-DUP-01..U-DUP-08).

Targets
-------
* [`extract_uniques()`](clean_duplicates_and_build_dataset.py:68)
* [`clean_duplicates()`](clean_duplicates_and_build_dataset.py:142)

The module is never imported at test-module level: it is obtained through the
``clean_duplicates_module`` fixture, which loads it under the stable alias
``dynamtests_clean_duplicates`` (obstacle O2).  ``main()`` is never called, because
its defaults point at hard-coded ``E:/000_Tesis/...`` paths
([`clean_duplicates_and_build_dataset.py:177-189`](clean_duplicates_and_build_dataset.py:177)).

Pinned known bug (O7) -- U-DUP-03
---------------------------------
[`extract_uniques()`](clean_duplicates_and_build_dataset.py:68) concatenates the
two bodies at [`clean_duplicates_and_build_dataset.py:103`](clean_duplicates_and_build_dataset.py:103)
*before* the ``is None`` guard at
[`clean_duplicates_and_build_dataset.py:115`](clean_duplicates_and_build_dataset.py:115).
Therefore a ``None`` ``test_case['body']`` never reaches the intended filter:

    TypeError: can only concatenate str (not "NoneType") to str

raised from line 103, and the per-repository output folder is never created
(``os.makedirs`` happens later, at
[`clean_duplicates_and_build_dataset.py:128`](clean_duplicates_and_build_dataset.py:128)).
U-DUP-03 pins that behaviour with ``@pytest.mark.regression``; the desired
behaviour (skip the record, return ``(0, 1)``) is U-DUP-04, tagged
``@pytest.mark.xfail_spoon`` and made a strict xfail with
``@pytest.mark.xfail(strict=True, ...)`` -- the same stacking used by U-MAP-07 in
``tests/unit/test_match_test_cases.py`` (``xfail_spoon`` is only a tag).

Determinism notes
-----------------
``extract_uniques()`` iterates ``os.listdir()`` / ``next(os.walk())[1]``, whose
order is filesystem dependent.  Assertions therefore use counts and sets; where a
single file must be identified, membership is asserted against the set of
candidates instead of a fixed file name.

Every write goes below ``tmp_path``; the fixture trees come from
``mining_tmp_tree`` and all output roots are ``tmp_path``-based.  No
``.rooignore``d directory is read or written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Local helpers (not fixtures: reused by several tests in this module only)
# ---------------------------------------------------------------------------
def _prepare_repo(mining_root: Path, split: str, repo_id: str = "123") -> Path:
    """Return ``<mining_root>/<split>/output/<repo_id>`` with no pre-existing files.

    ``mining_tmp_tree`` ships two synthetic JSON files per split; each test that
    needs exact contents empties the folder first so the assertions do not depend
    on the fixture payload.
    """
    repo_dir = mining_root / split / "output" / repo_id
    repo_dir.mkdir(parents=True, exist_ok=True)
    for stale in repo_dir.iterdir():
        if stale.is_file():
            stale.unlink()
    return repo_dir


def _write_record(repo_dir: Path, name: str, record: dict) -> Path:
    """Serialise ``record`` as ``repo_dir/name`` and return the path."""
    path = repo_dir / name
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# U-DUP-01 -- identical (body_focal, body_test) pair is kept once
# ---------------------------------------------------------------------------
def test_u_dup_01_extract_uniques_identical_pair_accepts_one(
    clean_duplicates_module, mining_tmp_tree, make_mtc_json, tmp_path
):
    repo_dir = _prepare_repo(mining_tmp_tree, "train")
    record = make_mtc_json()
    _write_record(repo_dir, "a.json", record)
    _write_record(repo_dir, "b.json", record)

    path_in = mining_tmp_tree / "train" / "output"
    path_out = tmp_path / "dataset" / "train"

    accepted, ignored = clean_duplicates_module.extract_uniques(
        "train", set(), set(), str(path_in), str(path_out)
    )

    # The second occurrence of the same ``method + test`` concatenation hits
    # ``pair_test_and_focal in unique_all_tests``
    # (clean_duplicates_and_build_dataset.py:115-119).
    assert (accepted, ignored) == (1, 1)

    # Only one file is copied into dataset/train/<repo_id>/
    # (clean_duplicates_and_build_dataset.py:129-132).  Which one wins depends
    # on os.listdir(), so only membership is asserted.
    copied = sorted(p.name for p in (path_out / "123").iterdir())
    assert len(copied) == 1
    assert copied[0] in {"a.json", "b.json"}


# ---------------------------------------------------------------------------
# U-DUP-02 -- the key is NOT normalised: whitespace variants are all kept
# ---------------------------------------------------------------------------
@pytest.mark.regression
def test_u_dup_02_extract_uniques_whitespace_variants_are_not_deduplicated(
    clean_duplicates_module, mining_tmp_tree, make_mtc_json, tmp_path
):
    repo_dir = _prepare_repo(mining_tmp_tree, "train")
    baseline = make_mtc_json()
    variant = make_mtc_json(
        body_focal='public  String  doSomething(int  val)  {  return "value";  }',
        body_test=(
            "public void testDoSomething() {  "
            'Assert.assertEquals("value", new SampleFocal().doSomething(1));   }'
        ),
    )
    _write_record(repo_dir, "plain.json", baseline)
    _write_record(repo_dir, "spaced.json", variant)

    unique_tests = set()
    path_in = mining_tmp_tree / "train" / "output"
    path_out = tmp_path / "dataset" / "train"

    accepted, ignored = clean_duplicates_module.extract_uniques(
        "train", unique_tests, set(), str(path_in), str(path_out)
    )

    # PINNED current behaviour: the concatenation at line 103 is compared as a
    # raw string, so tab/space differences make both pairs "unique".
    assert (accepted, ignored) == (2, 0)
    assert len(unique_tests) == 2
    assert sorted(p.name for p in (path_out / "123").iterdir()) == [
        "plain.json",
        "spaced.json",
    ]


# ---------------------------------------------------------------------------
# U-DUP-03 -- O7: None body raises TypeError before the None filter
# ---------------------------------------------------------------------------
@pytest.mark.regression
def test_u_dup_03_extract_uniques_none_test_body_raises_type_error(
    clean_duplicates_module, mining_tmp_tree, make_mtc_json, tmp_path
):
    repo_dir = _prepare_repo(mining_tmp_tree, "train")
    record = make_mtc_json()
    record["test_case"]["body"] = None
    _write_record(repo_dir, "none_body.json", record)

    path_in = mining_tmp_tree / "train" / "output"
    path_out = tmp_path / "dataset" / "train"

    # Line 103 concatenates *before* the ``test_src_code is None`` branch at
    # line 115, so the guard is unreachable and ``str + None`` raises.
    with pytest.raises(TypeError, match="can only concatenate str"):
        clean_duplicates_module.extract_uniques(
            "train", set(), set(), str(path_in), str(path_out)
        )

    # The repository output folder is created only after the filter
    # (clean_duplicates_and_build_dataset.py:128), so the abort leaves no trace.
    assert not (path_out / "123").exists()


# ---------------------------------------------------------------------------
# U-DUP-04 -- desired behaviour: discard the None record instead of aborting
# ---------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, reason="desired behaviour after the Spoon migration (TEST_PLAN U-DUP-04)")
@pytest.mark.xfail_spoon
def test_u_dup_04_extract_uniques_should_ignore_none_test_body(
    clean_duplicates_module, mining_tmp_tree, make_mtc_json, tmp_path
):
    repo_dir = _prepare_repo(mining_tmp_tree, "train")
    record = make_mtc_json()
    record["test_case"]["body"] = None
    _write_record(repo_dir, "none_body.json", record)

    accepted, ignored = clean_duplicates_module.extract_uniques(
        "train",
        set(),
        set(),
        str(mining_tmp_tree / "train" / "output"),
        str(tmp_path / "dataset" / "train"),
    )

    # Desired post-migration contract (TEST_PLAN U-DUP-04).  Today this test
    # fails with the TypeError pinned by U-DUP-03, hence the strict xfail.
    assert (accepted, ignored) == (0, 1)


# ---------------------------------------------------------------------------
# U-DUP-05 -- Defects4J URLs are filtered by exact string match
# ---------------------------------------------------------------------------
def test_u_dup_05_extract_uniques_excludes_defects4j_urls(
    clean_duplicates_module, mining_tmp_tree, make_mtc_json, tmp_path
):
    # The literal with the trailing slash is the one present in the frozenset
    # (clean_duplicates_and_build_dataset.py:37).
    d4j_url = "https://github.com/apache/commons-lang/"
    assert d4j_url in clean_duplicates_module.DEFECTS4J_PROJECTS_URLS
    assert "https://github.com/apache/commons-lang" not in (
        clean_duplicates_module.DEFECTS4J_PROJECTS_URLS
    )

    repo_dir = _prepare_repo(mining_tmp_tree, "train")
    _write_record(repo_dir, "d4j.json", make_mtc_json(url=d4j_url))

    path_out = tmp_path / "dataset" / "train"
    accepted, ignored = clean_duplicates_module.extract_uniques(
        "train",
        set(),
        set(),
        str(mining_tmp_tree / "train" / "output"),
        str(path_out),
    )

    # Exact-match exclusion (clean_duplicates_and_build_dataset.py:99-101).
    assert (accepted, ignored) == (0, 1)
    assert not (path_out / "123").exists()

    # The same URL without the trailing slash is *not* in the set, so it is
    # accepted: the filter is a plain membership test, not a prefix match.
    plain_root = tmp_path / "plain_mining"
    plain_repo = _prepare_repo(plain_root, "train")
    _write_record(
        plain_repo,
        "plain_url.json",
        make_mtc_json(url="https://github.com/apache/commons-lang"),
    )

    accepted_plain, ignored_plain = clean_duplicates_module.extract_uniques(
        "train",
        set(),
        set(),
        str(plain_root / "train" / "output"),
        str(tmp_path / "plain_dataset" / "train"),
    )
    assert (accepted_plain, ignored_plain) == (1, 0)


# ---------------------------------------------------------------------------
# U-DUP-06 -- clean_duplicates(): train is processed first, test loses the pair
# ---------------------------------------------------------------------------
def test_u_dup_06_clean_duplicates_train_precedes_test(
    clean_duplicates_module, mining_tmp_tree, make_mtc_json, tmp_path, capsys
):
    record = make_mtc_json()
    for split in ("train", "test"):
        repo_dir = _prepare_repo(mining_tmp_tree, split)
        _write_record(repo_dir, "same.json", record)

    output_root = tmp_path / "dataset"
    clean_duplicates_module.clean_duplicates(str(mining_tmp_tree), str(output_root))

    train_repo = output_root / "train" / "123"
    assert sorted(p.name for p in train_repo.iterdir()) == ["same.json"]
    # The same pair was already registered while reading train/output
    # (clean_duplicates_and_build_dataset.py:158) so test/output ignores it
    # (clean_duplicates_and_build_dataset.py:162) and creates no repo folder.
    assert not (output_root / "test" / "123").exists()

    stdout = capsys.readouterr().out
    assert "Accepted / Ignored tests Train: 1 / 0" in stdout
    assert "Accepted / Ignored tests Test: 0 / 1" in stdout


# ---------------------------------------------------------------------------
# U-DUP-07 -- missing input path is a no-op returning (0, 0)
# ---------------------------------------------------------------------------
def test_u_dup_07_extract_uniques_missing_input_path_returns_zero(
    clean_duplicates_module, tmp_path, capsys
):
    missing_input = tmp_path / "mining_does_not_exist"
    output_root = tmp_path / "dataset" / "train"

    accepted, ignored = clean_duplicates_module.extract_uniques(
        "train", set(), set(), str(missing_input), str(output_root)
    )

    # Early return at clean_duplicates_and_build_dataset.py:69-71.
    assert (accepted, ignored) == (0, 0)
    assert f"Not exists path: {missing_input}" in capsys.readouterr().out
    # No output tree is created from the early return.
    assert not output_root.exists()


# ---------------------------------------------------------------------------
# U-DUP-08 -- clean_duplicates() unconditionally creates the three splits
# ---------------------------------------------------------------------------
def test_u_dup_08_clean_duplicates_creates_empty_split_folders(
    clean_duplicates_module, tmp_path
):
    empty_input = tmp_path / "empty_mining"
    output_root = tmp_path / "dataset"

    clean_duplicates_module.clean_duplicates(str(empty_input), str(output_root))

    # os.makedirs at clean_duplicates_and_build_dataset.py:151-153 runs before
    # any input is inspected, so the three splits exist even with no input.
    for split in ("train", "validation", "test"):
        split_dir = output_root / split
        assert split_dir.is_dir()
        assert list(split_dir.iterdir()) == []
