"""End-to-end mini-pipeline tests (TEST_PLAN section B.11, E-01..E-03).

What is chained (real production functions, no reimplementation)
---------------------------------------------------------------
A single workspace (``tmp_path_factory.mktemp(...)``) is filled stage by stage,
each stage consuming the *real* artefacts of the previous one:

1. **Stage 1 - mining / mapping**
   [`find_map_test_cases()`](find_map_tests_cases_from_repo.py:192) over a
   ``tmp_path`` copy of [`sample_java_repo`](tests/fixtures/java/sample_java_repo/src/main)
   in which two test classes are present (see "Fixture tailoring" below). It
   writes the mapped-test-case JSONs (``<repo_id>_<i>.json``) through
   [`export_mtc()`](find_map_tests_cases_from_repo.py:679) plus ``log.txt``.
2. **Stage 2 - dedup / dataset**
   [`clean_duplicates()`](clean_duplicates_and_build_dataset.py:142) over
   ``mining/{train,validation,test}/output/<repo_id>/``, with the stage-1 output
   copied into the three splits so that the *train-wins* precedence of
   [`extract_uniques()`](clean_duplicates_and_build_dataset.py:68) is exercised.
3. **Stage 3 - corpus format**
   [`build_corpus()`](build_corpus.py:80) over ``dataset/train/``, which runs the
   real syntactic filters of
   [`extract_data_from_mapped_test_case()`](build_corpus.py:328) -- including the
   empty-body rejection at [`build_corpus.py:360-364`](build_corpus.py:360) --
   and [`build_format_corpus()`](build_corpus.py:416).
4. **Stage 4 - CSV**
   [`convert()`](convert_json_corpus_to_csv_input.py:25) over
   ``corpus/json/train/``.

Stage 1 artefacts asserted by E-01
----------------------------------
* ``mining/train/output/<repo_id>/`` holds three exported JSONs (one per mapped
  test case) whose five top-level keys are the ``export_mtc()`` contract.
* ``dataset/train/<repo_id>/`` holds the same three files; ``dataset/validation``
  and ``dataset/test`` contain **no** per-repository folder because the copies of
  the train records are duplicates (shared ``unique_all_tests`` set).
* ``corpus/json/train/<repo_id>/`` holds **two** ``*_corpus.json`` files with the
  six canonical keys: the third mapped test case targets
  ``FocalContext.runSomeVoid(String)``, whose body is empty, so the real filter
  at [`build_corpus.py:360-364`](build_corpus.py:360) drops it. This is why the
  plan's "two corpus rows" hold even though stage 1 exported three records.
* ``corpus/raw/train/`` holds the six ``.txt`` files, two lines each.
* ``corpus/csv/train.csv`` holds two rows and the header pinned by U-CSV-01.

Fixture tailoring (and why)
---------------------------
* The stock [`FocalContextTest.java`](tests/fixtures/java/sample_java_repo/src/test/com/eljavatar/focals/FocalContextTest.java:1)
  is rewritten *inside the tmp copy only* to keep just ``testDoSomething()``
  (name-matching heuristic) and ``verifyBehaviour()`` (single-invocation
  heuristic). The remaining five fixture methods exist to lock the mapping
  heuristics (U-MAP-*) and would add noise to the pipeline counts; the mapping
  stage itself is still the real one.
* One extra test class, ``SamePackageExternal01Test``, is written into the tmp
  copy so that two *distinct* focal methods reach the corpus stage; otherwise
  the only non-empty focal body (``doSomething``) produces a single record and
  the plan's two-row expectations could not be observed without synthetic JSONs.
* The repository URL is ``https://example.invalid/sample-repo`` on purpose:
  [`DEFECTS4J_PROJECTS_URLS`](clean_duplicates_and_build_dataset.py:29) is a
  literal blacklist applied at
  [`clean_duplicates_and_build_dataset.py:99-101`](clean_duplicates_and_build_dataset.py:99),
  so any Defects4J URL (including the first entry of
  [`repos_prueba.json`](tests/fixtures/repos_prueba.json:1)) would be dropped by design.

Hermeticity
-----------
``subprocess.check_output`` (the ``grep`` of stage 1) is replaced by a
deterministic fake, ``os.chdir`` is done through ``pytest.MonkeyPatch`` so the
original working directory is restored, and the autouse ``no_network`` guard of
``tests/conftest.py`` stays active. Every write happens below ``tmp_path``; no
``.rooignore`` path is read or written. No production file was modified.

E-02 -- isolation, pinned as a real assertion
---------------------------------------------
The session ``no_network`` fixture patches ``socket``/``urllib`` (and, when
GitPython is already imported, ``git.Repo.clone_from``). E-02 asserts those
guards by *using* them, then proves that the production clone path
([`clone_repo()`](find_map_tests_cases_from_repo.py:82)) really delegates to
``git.Repo.clone_from`` and propagates its failure, without opening a socket.
GitPython is imported lazily by ``find_map_tests_cases_from_repo.py``, i.e.
*after* the session fixture ran, so the session guard on ``git.Repo`` is
normally absent; the test therefore checks it only when present and always
checks the delegation with a recording stub (see the README for details).

Runtime
-------
The whole module is fast (well below the one-second-per-test ``slow`` budget
that would silently exclude it from the default ``-m "not slow"`` selection),
so no test is marked ``slow``.
"""

from __future__ import annotations

import json
import shutil
import socket
import urllib.request
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import pytest

#: The mini-pipeline is the end-to-end level of the suite (TEST_PLAN section D.1).
pytestmark = [pytest.mark.e2e]


# ---------------------------------------------------------------------------
# Constants shared by the whole module
# ---------------------------------------------------------------------------
REPO_ID = "123"

#: Non-Defects4J URL: Defects4J repositories are blacklisted by URL
#: ([`clean_duplicates_and_build_dataset.py:29-47`](clean_duplicates_and_build_dataset.py:29)).
REPO_URL = "https://example.invalid/sample-repo"

#: Name of the project folder created below ``<workspace>/projects``.
PROJECT_DIR_NAME = "java_project"

#: Test classes listed to stage 1 (relative to the project folder). The fake
#: ``grep`` returns exactly these, so the listing is deterministic.
TEST_CLASS_FOCAL_CONTEXT = "src/test/com/eljavatar/focals/FocalContextTest.java"
TEST_CLASS_SAME_PACKAGE = "src/test/com/eljavatar/focals/SamePackageExternal01Test.java"

#: Minimal ``FocalContextTest`` (two heuristics: name match + single invocation).
FOCAL_CONTEXT_TEST_SOURCE = """package com.eljavatar.focals;

import org.junit.Test;

import static org.junit.Assert.assertEquals;

/**
 * Trimmed copy written by tests/e2e/test_mini_pipeline.py into a tmp tree.
 * Only the two methods that the mini-pipeline needs are kept: one matched by
 * name and one matched by a unique method invocation.
 */
public class FocalContextTest {

    @Test
    public void testDoSomething() {
        assertEquals("value", new FocalContext().doSomething(null, null, null, null, null));
    }

    @Test
    public void verifyBehaviour() {
        new FocalContext().runSomeVoid("x");
    }
}
"""

#: Second test class, so that two distinct focal methods reach the corpus stage.
SAME_PACKAGE_TEST_SOURCE = """package com.eljavatar.focals;

import org.junit.Test;

/**
 * Trimmed copy written by tests/e2e/test_mini_pipeline.py into a tmp tree.
 * The single invocation heuristic maps this test case to
 * SamePackageExternal01.getSomeStrFromSamePackExt01().
 */
public class SamePackageExternal01Test {

    @Test
    public void verifyGetSomeStrFromSamePackage() {
        new SamePackageExternal01().getSomeStrFromSamePackExt01();
    }
}
"""

#: Corpus tags, mirroring the CLI defaults pinned by U-CLI-03.
TAGS = (
    "<FCTX>",
    "</FCTX>",
    "<ECTX>",
    "</ECTX>",
    "<PRIVATE_FCTX>",
    "</PRIVATE_FCTX>",
)

#: Keys of one corpus JSON record (stage 3 contract).
CORPUS_KEYS = (
    "target",
    "src_fm_fc_ms_ff",
    "src_fm_fc_dctx",
    "src_fm_fc_dctx_priv",
    "imports_focal_class",
    "imports_test_class",
)

#: Keys of one mining JSON record (stage 1 contract, ``export_mtc()``).
MINING_KEYS = ("test_class", "test_case", "focal_class", "focal_method", "repository")

#: The six raw-corpus files, in the same order as ``RAW_KEYS``.
RAW_FILES = (
    "input_methods_src_fm_fc_ms_ff.txt",
    "input_methods_src_fm_fc_dctx.txt",
    "input_methods_src_fm_fc_dctx_priv.txt",
    "output_tests.txt",
    "imports_focal_class.txt",
    "imports_test_class.txt",
)

#: Corpus keys in the exact order in which ``export_corpus_raw()`` writes them
#: ([`build_corpus.py:319-325`](build_corpus.py:319)).
RAW_KEYS = (
    "src_fm_fc_ms_ff",
    "src_fm_fc_dctx",
    "src_fm_fc_dctx_priv",
    "target",
    "imports_focal_class",
    "imports_test_class",
)

#: Number of mapped test cases exported by stage 1 (2 x FocalContextTest +
#: 1 x SamePackageExternal01Test).
EXPECTED_MAPPED = 3

#: Number of records that survive the empty-body filter of stage 3.
EXPECTED_CORPUS = 2


# ---------------------------------------------------------------------------
# Module-local helpers (no fixture is added to tests/conftest.py)
# ---------------------------------------------------------------------------
def _materialise_java_project(java_classes_root: Path, workspace: Path) -> Path:
    """Copy the fixture project into *workspace* and tailor its test sources.

    Only the ``src/`` subtree is copied (that is all ``find_map_test_cases()``
    walks). The two test classes are rewritten/created **inside the copy**.
    """
    project = workspace / "projects" / PROJECT_DIR_NAME
    shutil.copytree(java_classes_root / "src", project / "src")

    (project / TEST_CLASS_FOCAL_CONTEXT).write_text(
        FOCAL_CONTEXT_TEST_SOURCE, encoding="utf-8"
    )
    same_package_test = project / TEST_CLASS_SAME_PACKAGE
    same_package_test.parent.mkdir(parents=True, exist_ok=True)
    same_package_test.write_text(SAME_PACKAGE_TEST_SOURCE, encoding="utf-8")
    return project


def _fake_grep_listing() -> bytes:
    """Byte payload emulating ``grep -l -r @Test`` run from ``<workspace>/projects``.

    ``find_map_test_cases()`` normalises test paths with
    ``replace("/src/test/", "/src/main/")``
    ([`find_map_tests_cases_from_repo.py:289`](find_map_tests_cases_from_repo.py:289)),
    so the payload must keep the ``<project>/src/test/...`` shape that a real
    ``grep -r`` prints when executed from the parent of the project.
    """
    lines = [
        f"{PROJECT_DIR_NAME}/{TEST_CLASS_FOCAL_CONTEXT}",
        f"{PROJECT_DIR_NAME}/{TEST_CLASS_SAME_PACKAGE}",
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


def _run_mining_stage(project: Path, mining_root: Path, fm_repo_module) -> Tuple:
    """Run the real stage 1 and return its 7-tuple result.

    ``subprocess.check_output`` (the ``grep`` call at
    [`find_map_tests_cases_from_repo.py:220`](find_map_tests_cases_from_repo.py:220))
    is replaced by the deterministic listing; ``os.chdir`` performed by the
    production code is undone through ``pytest.MonkeyPatch.undo()``.
    """
    projects_root = project.parent
    output = mining_root / "train" / "output" / REPO_ID
    output.mkdir(parents=True)

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.chdir(projects_root)
        monkeypatch.setattr(
            fm_repo_module.subprocess,
            "check_output",
            lambda *_args, **_kwargs: _fake_grep_listing(),
        )
        return fm_repo_module.find_map_test_cases(
            str(projects_root),
            "java",
            str(output),
            {"repo_id": REPO_ID, "url": REPO_URL},
            False,
        )
    finally:
        monkeypatch.undo()


def _copy_train_records_to_other_splits(mining_root: Path) -> None:
    """Copy the train mining JSONs into ``validation`` and ``test``.

    This is what makes stage 2 interesting: the three records are duplicated
    across splits, and ``clean_duplicates()`` must keep them in ``train`` only.
    """
    train_repo = mining_root / "train" / "output" / REPO_ID
    records = sorted(train_repo.glob("*.json"))
    assert len(records) == EXPECTED_MAPPED, (
        "stage 1 must have exported one JSON per mapped test case, got "
        f"{[path.name for path in records]}"
    )
    for split in ("validation", "test"):
        target_dir = mining_root / split / "output" / REPO_ID
        target_dir.mkdir(parents=True, exist_ok=True)
        for record in records:
            shutil.copy2(record, target_dir / record.name)


def _load_corpus_records(split_dir: Path) -> List[Dict[str, Any]]:
    """Every ``*_corpus.json`` record of a split, read from disk."""
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(split_dir.glob("*/*_corpus.json"))
    ]


def _read_raw_lines(raw_dir: Path) -> Dict[str, List[str]]:
    """``{file_name: lines}`` for the six raw-corpus files."""
    return {
        name: (raw_dir / name).read_text(encoding="utf-8").splitlines()
        for name in RAW_FILES
    }


# ---------------------------------------------------------------------------
# Module-scoped pipeline run (E-01 builds it, E-03 consumes it)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def pipeline_run(
    tmp_path_factory: pytest.TempPathFactory,
    java_classes_root: Path,
    parser_utils,
    fm_repo_module,
    clean_duplicates_module,
    build_corpus_module,
    convert_csv_module,
) -> SimpleNamespace:
    """Run mining -> dedup -> corpus -> CSV once and expose every artefact.

    ``tmp_path_factory`` is used instead of ``tmp_path`` because the run must be
    shared by E-01 (artefact counts) and E-03 (corpus invariants), which are two
    separate test functions.
    """
    workspace = tmp_path_factory.mktemp("mini_pipeline")

    # Stage 1 -- mining / mapping.
    project = _materialise_java_project(java_classes_root, workspace)
    mining_root = workspace / "mining"
    mining_result = _run_mining_stage(project, mining_root, fm_repo_module)
    _copy_train_records_to_other_splits(mining_root)

    # Stage 2 -- dedup / dataset.
    dataset_root = workspace / "dataset"
    clean_duplicates_module.clean_duplicates(str(mining_root), str(dataset_root))

    # Stage 3 -- corpus format.
    corpus_root = workspace / "corpus"
    build_corpus_module.build_corpus(
        parser_utils,
        {},
        str(dataset_root / "train"),
        "utf-8",
        str(corpus_root),
        "train",
        *TAGS,
    )

    # Stage 4 -- CSV.
    json_split = corpus_root / "json" / "train"
    csv_root = corpus_root / "csv"
    convert_csv_module.convert("train", str(json_split), str(csv_root))

    return SimpleNamespace(
        workspace=workspace,
        project=project,
        mining_root=mining_root,
        mining_result=mining_result,
        dataset_root=dataset_root,
        corpus_root=corpus_root,
        json_split=json_split,
        raw_dir=corpus_root / "raw" / "train",
        csv_path=csv_root / "train.csv",
    )


# ---------------------------------------------------------------------------
# E-01 -- the whole chain produces the planned artefacts
# ---------------------------------------------------------------------------
def test_e_01_mini_pipeline_builds_dataset_corpus_and_csv(pipeline_run) -> None:
    """E-01: mining -> dedup -> corpus -> CSV over one ``tmp_path`` workspace."""
    run = pipeline_run

    # ---- stage 1: three mapped test cases, real export_mtc() artefacts -------
    assert run.mining_result == (2, 3, 2, EXPECTED_MAPPED, True, True, False)

    mining_dir = run.mining_root / "train" / "output" / REPO_ID
    assert sorted(path.name for path in mining_dir.glob("*.json")) == [
        f"{REPO_ID}_{index}.json" for index in range(EXPECTED_MAPPED)
    ]
    for path in sorted(mining_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        assert set(MINING_KEYS) <= set(record)
        assert record["repository"] == {"repo_id": REPO_ID, "url": REPO_URL}
        # ``export_mtc()`` strips the body from every focal_class method
        # ([`find_map_tests_cases_from_repo.py:693-701`](find_map_tests_cases_from_repo.py:693)).
        for method in record["focal_class"]["methods"]:
            assert "body" not in method

    # ---- stage 2: all three survive in train, no per-repo folder elsewhere ---
    dataset_dir = run.dataset_root / "train" / REPO_ID
    assert sorted(path.name for path in dataset_dir.glob("*.json")) == [
        f"{REPO_ID}_{index}.json" for index in range(EXPECTED_MAPPED)
    ]
    assert not (run.dataset_root / "validation" / REPO_ID).exists()
    assert not (run.dataset_root / "test" / REPO_ID).exists()

    # ---- stage 3: two corpus records (empty-body record filtered out) -------
    corpus_files = sorted(run.json_split.glob(f"{REPO_ID}/*_corpus.json"))
    assert len(corpus_files) == EXPECTED_CORPUS
    corpus_records = _load_corpus_records(run.json_split)
    assert len(corpus_records) == EXPECTED_CORPUS
    for record in corpus_records:
        assert tuple(record.keys()) == CORPUS_KEYS
        assert record["target"]
        assert "<FCTX>" in record["src_fm_fc_dctx"]
        assert "</FCTX>" in record["src_fm_fc_dctx"]
        assert "<ECTX>" in record["src_fm_fc_dctx"]

    # The two surviving focal classes are the real ones mined from the tree.
    l1_sources = [record["src_fm_fc_ms_ff"] for record in corpus_records]
    assert any(source.startswith("public class FocalContext") for source in l1_sources)
    assert any(
        source.startswith("public class SamePackageExternal01") for source in l1_sources
    )

    # ---- stage 3: the six raw files, two aligned lines each ------------------
    assert sorted(path.name for path in run.raw_dir.iterdir()) == sorted(RAW_FILES)
    for name, lines in _read_raw_lines(run.raw_dir).items():
        assert len(lines) == EXPECTED_CORPUS, f"{name} must have one line per record"

    # ---- stage 4: the CSV has the pinned header and one row per record ------
    pd = pytest.importorskip("pandas")
    df = pd.read_csv(run.csv_path, dtype=str, keep_default_na=False)
    assert df.columns.tolist() == list(CORPUS_KEYS)
    assert len(df) == EXPECTED_CORPUS
    assert (df["target"] != "").all()
    assert set(df["target"]) == {record["target"] for record in corpus_records}


# ---------------------------------------------------------------------------
# E-02 -- no network, no clone
# ---------------------------------------------------------------------------
def test_e_02_network_and_clone_paths_are_blocked(
    tmp_path: Path,
    fm_repo_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E-02: the network guards are effective and the clone path cannot escape them.

    Part 1 *uses* the guards installed by the autouse ``no_network`` fixture, so
    the test fails loudly (an unresolvable ``.invalid`` host raises
    ``socket.gaierror``, not ``AssertionError``) if the fixture stops protecting
    the suite. Part 2 pins that ``clone_repo()`` really goes through
    ``git.Repo.clone_from`` and propagates its failure: no clone is attempted.
    """
    # ---- part 1: socket / urllib guards from the autouse fixture ------------
    with pytest.raises(AssertionError, match="Network access is forbidden"):
        socket.create_connection(("example.invalid", 443))

    probe_socket = socket.socket()
    try:
        with pytest.raises(AssertionError, match="Network access is forbidden"):
            probe_socket.connect(("example.invalid", 443))
    finally:
        probe_socket.close()

    with pytest.raises(AssertionError, match="Network access is forbidden"):
        urllib.request.urlopen("https://example.invalid/resource")

    # ---- part 2: the production clone path --------------------------------
    git_module = pytest.importorskip("git")

    # GitPython is imported lazily by find_map_tests_cases_from_repo.py, i.e.
    # after the session fixture ran, so the session-level guard on
    # ``git.Repo.clone_from`` is usually absent. Assert it when present.
    if getattr(git_module.Repo.clone_from, "__name__", "") == "_forbidden":
        with pytest.raises(AssertionError, match="Network access is forbidden"):
            git_module.Repo.clone_from(
                "https://example.invalid/repo.git", str(tmp_path / "guarded")
            )

    clone_attempts: List[Tuple[Any, ...]] = []

    def _refuse_clone(*args: Any, **_kwargs: Any):
        clone_attempts.append(args)
        raise AssertionError("git clone attempted: the e2e suite must stay offline")

    monkeypatch.setattr(git_module.Repo, "clone_from", staticmethod(_refuse_clone))
    # ``clone_repo()`` is wrapped by ``retry(wait=3, retries=3)``
    # ([`find_map_tests_cases_from_repo.py:81`](find_map_tests_cases_from_repo.py:81));
    # neutralise the 3-second sleeps so the four attempts stay instant.
    monkeypatch.setattr(fm_repo_module.time, "sleep", lambda *_a, **_k: None)

    clone_target = tmp_path / "cloned"
    with pytest.raises(AssertionError, match="git clone attempted"):
        fm_repo_module.clone_repo(
            REPO_ID,
            "https://test-user:test-token@example.invalid/repo.git",
            str(clone_target),
        )

    # 1 initial attempt + 3 retries, and nothing was materialised on disk.
    assert len(clone_attempts) == 4
    assert not clone_target.exists()


# ---------------------------------------------------------------------------
# E-03 -- corpus invariants: raw <-> json <-> csv stay aligned
# ---------------------------------------------------------------------------
def test_e_03_raw_json_and_csv_stay_aligned(pipeline_run) -> None:
    """E-03: same line/row count everywhere and no index misalignment."""
    pd = pytest.importorskip("pandas")

    raw_lines = _read_raw_lines(pipeline_run.raw_dir)
    corpus_records = _load_corpus_records(pipeline_run.json_split)
    df = pd.read_csv(pipeline_run.csv_path, dtype=str, keep_default_na=False)

    # ---- 1) every artefact has the same number of entries -------------------
    line_counts = {name: len(lines) for name, lines in raw_lines.items()}
    assert set(line_counts.values()) == {EXPECTED_CORPUS}, line_counts
    assert len(corpus_records) == EXPECTED_CORPUS
    assert len(df) == EXPECTED_CORPUS

    # ---- 2) raw rows and JSON records are the same multiset of 6-tuples ----
    raw_tuples = Counter(
        tuple(raw_lines[name][index] for name in RAW_FILES)
        for index in range(EXPECTED_CORPUS)
    )
    json_tuples = Counter(
        tuple(record[key] for key in RAW_KEYS) for record in corpus_records
    )
    assert raw_tuples == json_tuples

    # ---- 3) the CSV rows are the same 6-tuples as the JSON records --------
    csv_tuples = Counter(
        tuple(row[key] for key in RAW_KEYS) for row in df.to_dict(orient="records")
    )
    assert csv_tuples == json_tuples

    # ---- 4) no cross-file misalignment: line i of every raw file belongs to
    #         the same record (checked through the focal-class marker) -------
    for index in range(EXPECTED_CORPUS):
        l1_line = raw_lines["input_methods_src_fm_fc_ms_ff.txt"][index]
        dctx_line = raw_lines["input_methods_src_fm_fc_dctx.txt"][index]
        dctx_priv_line = raw_lines["input_methods_src_fm_fc_dctx_priv.txt"][index]
        focal_class = l1_line.split(" { ")[0]
        assert focal_class in dctx_line
        assert focal_class in dctx_priv_line
