# DynaMTests — test suite guide

Hermetic `pytest` suite for the DynaMTests pipeline (stages 1–7 of
[`PIPELINE_STEPS.md`](PIPELINE_STEPS.md:1)). The contract of every test id is
[`tests/TEST_PLAN.md`](tests/TEST_PLAN.md:1); this file explains how to install,
run and extend it.

Current baseline (Python 3.9.13, `pytest` 8.4.2, `tree-sitter` 0.23.2):

```text
python -m pytest tests -q -p no:warnings
73 passed, 5 xfailed
```

---

## 1) Requirements and installation

The suite only needs the *dev* tooling on top of the pipeline's own runtime
dependencies:

```bash
python -m pip install pytest pytest-mock
```

Runtime dependencies imported by the production scripts that the tests exercise
(install them if the pipeline itself runs on the machine):

```text
tree-sitter            # installed here as 0.23.2 (see §6)
tree-sitter-java
pandas                 # stage 4 (convert_json_corpus_to_csv_input.py)
GitPython              # stage 1 (find_map_tests_cases_from_repo.py)
tqdm                   # progress bars used by stages 2 and 3
command_runner         # stage 1 (elevate helpers)
packaging
```

Import guards: every module that needs an optional dependency calls
`pytest.importorskip(...)` before importing it (module-level or inside the
fixture), so a partial environment produces **skips**, never collection errors:

| Missing package | Effect |
|---|---|
| `tree_sitter` | AST/parser/dependency/mapping tests skip |
| `pandas` | `tests/unit/test_convert_csv.py` and the CSV assertions of `tests/e2e/` skip |
| `git`, `command_runner` | `fm_repo_module` and everything built on it skip |
| `tqdm` | stage 2/3 modules skip |

No package needs to be installed for the pipeline scripts themselves: the repo
root is added to `sys.path` by [`tests/conftest.py`](tests/conftest.py:43).

### GitHub credentials

[`find_map_tests_cases_from_repo.py:32-33`](find_map_tests_cases_from_repo.py:32)
reads `GITHUB_USER` / `GITHUB_TOKEN` at **import time** with direct indexing.
[`tests/conftest.py`](tests/conftest.py:37) sets both with
`os.environ.setdefault(...)` *before* any production module is imported, so the
suite works out of the box. If you import the script outside pytest, export
dummy values first:

```bash
set GITHUB_USER=test-user
set GITHUB_TOKEN=test-token
```

---

## 2) How to run

All commands are executed from the repository root (`pytest.ini` is there):

| Goal | Command |
|---|---|
| Everything except `slow` (default selection) | `python -m pytest` |
| Verbose, same selection | `python -m pytest -v` |
| Unit only (fast loop) | `python -m pytest -m unit` |
| Integration only | `python -m pytest -m integration` |
| Regression only | `python -m pytest -m regression` |
| End-to-end mini-pipeline only | `python -m pytest -m e2e` |
| A single file | `python -m pytest tests/e2e/test_mini_pipeline.py -v` |
| Include `slow` tests | `python -m pytest -m "slow or not slow"` |
| Show why the strict xfails are strict | `python -m pytest tests/regression/test_spoon_desired.py -rxX` |
| Collect IDs only (no execution) | `python -m pytest --collect-only -q` |

[`pytest.ini`](pytest.ini:1) pins `testpaths = tests` and
`addopts = -ra -m "not slow"`; `--strict-markers` is **not** enabled, so a typo
in a marker silently drops the test from `-m` selections — see the troubleshooting
section below.

---

## 3) Markers

| Marker | Meaning | Where it is applied |
|---|---|---|
| `unit` | one pure function/module, disk access only through `tmp_path` | module level in `tests/unit/*.py` |
| `integration` | two or more production stages over a real temporary tree | module level in `tests/integration/*.py` |
| `e2e` | full mini-pipeline: mining → dedup → corpus → CSV | [`tests/e2e/test_mini_pipeline.py`](tests/e2e/test_mini_pipeline.py:1) |
| `slow` | expected to take more than one second; **excluded by default** | none today — do not use it for the e2e block unless the runtime really justifies it |
| `xfail_spoon` | desired behaviour *after* the Spoon migration; today it must keep failing (`strict=True` is stacked separately) | [`tests/regression/test_spoon_desired.py`](tests/regression/test_spoon_desired.py:1) and the mirrored unit tests |
| `regression` | locks a deliberately imperfect *current* behaviour | `tests/regression/test_known_bugs.py` and single unit tests |

Selection is marker based, so `-m "not slow"` (the default) never hides unit,
integration or e2e work.

---

## 4) Layout

```text
tests/
├── README.md                     # this file
├── TEST_PLAN.md                  # the contract: one row per test id
├── conftest.py                   # env bootstrap + sys.path + every shared fixture
├── helpers/module_loader.py      # load_module_from_path(): unique aliases for flat scripts
├── fixtures/
│   ├── metadata_samples.py       # hand-written {focal_class, focal_method} dicts
│   ├── mining_samples.py         # make_mtc_json() / make_corpus_record()
│   └── java/BrokenClass.java.txt # malformed Java source (parse_file error path)
├── unit/                         # 9 files, U-* ids
├── integration/                  # 2 files, I-* ids
├── regression/                   # 2 files, current-behaviour locks + Spoon-desired xfails
└── e2e/test_mini_pipeline.py     # E-01..E-03, mini-pipeline
```

`tests/e2e/` has no `__init__.py`, exactly like its siblings; pytest imports the
modules by path. No test module imports a production script at top level — the
scripts are reached through fixtures (see §5), which is what keeps
[`find_map_tests_cases_from_repo.py:32`](find_map_tests_cases_from_repo.py:32)
from raising `KeyError` at collection time.

---

## 5) Fixture catalogue ([`tests/conftest.py`](tests/conftest.py:1))

### 5.1 Global guards (autouse)

| Fixture | Scope | What it does |
|---|---|---|
| [`env_github`](tests/conftest.py:60) | session, autouse | `os.environ.setdefault` for `GITHUB_USER` / `GITHUB_TOKEN` (obstacle O1) |
| [`no_network`](tests/conftest.py:68) | session, autouse | replaces `socket.socket.connect`, `socket.socket.connect_ex`, `socket.create_connection`, `urllib.request.urlopen`, `git.Repo.clone_from` (when GitPython is already imported) and `requests.Session.request` (when imported) with a function that raises `AssertionError("Network access is forbidden ...")` |

### 5.2 Paths

| Fixture | Scope | Returns |
|---|---|---|
| [`repo_root`](tests/conftest.py:108) | session | repository root `Path` |
| [`tests_root`](tests/conftest.py:114) | session | `tests/` `Path` |
| [`myclass_java_path`](tests/conftest.py:120) | session | [`MyClass.java`](MyClass.java:1) at the repo root |
| [`java_classes_root`](tests/conftest.py:129) | session | [`000_java_classes_prueba`](000_java_classes_prueba/src/main) |
| [`java_main_root`](tests/conftest.py:138) | session | `…/src/main` |
| [`java_test_root`](tests/conftest.py:144) | session | `…/src/test` |
| [`focal_context_java`](tests/conftest.py:150) | session | `FocalContext.java` fixture file |
| [`focal_context_test_java`](tests/conftest.py:159) | session | `FocalContextTest.java` fixture file |
| [`broken_java_source`](tests/conftest.py:168) | session | `tests/fixtures/java/BrokenClass.java.txt` |

### 5.3 tree-sitter helpers (independent of the production parsers)

| Fixture | Scope | Returns |
|---|---|---|
| [`ts_java`](tests/conftest.py:189) | session | the `tree_sitter_java` module |
| [`java_language`](tests/conftest.py:195) | session | a `tree_sitter.Language` for Java, built for both the `< 0.22.0` and `>= 0.22.0` APIs |
| [`java_parser`](tests/conftest.py:210) | session | a configured `tree_sitter.Parser` (`set_language` vs constructor argument) |
| [`parse_java_source`](tests/conftest.py:227) | session | callable `parse(source) -> tree` accepting `str`/`bytes`/`Path` |

### 5.4 Production objects

| Fixture | Scope | Returns |
|---|---|---|
| [`parser_utils`](tests/conftest.py:246) | session | shared `ParserUtils("utf-8")` |
| [`class_parser`](tests/conftest.py:255) | function | fresh `ClassParser("java")` (the instance is stateful) |
| [`dependency_class_parser`](tests/conftest.py:264) | function | fresh `DependencyClassParser("java")` |
| [`dependency_parser_utils`](tests/conftest.py:273) | session | `DependencyParserUtils()` static-helper container |

### 5.5 Project-script loaders (obstacle O2: colliding module names)

All of them return the module loaded from disk under a unique alias, so
`build_corpus` and `build_corpus_d4j` can coexist in one process.

| Fixture | Scope | Alias |
|---|---|---|
| [`load_project_module`](tests/conftest.py:285) | session | callable `load(relative_path, alias)` (backed by [`load_module_from_path()`](tests/helpers/module_loader.py:23)) |
| [`fm_repo_module`](tests/conftest.py:295) | module | `dynamtests_find_map` → [`find_map_tests_cases_from_repo.py`](find_map_tests_cases_from_repo.py:1) |
| [`build_corpus_module`](tests/conftest.py:310) | module | `dynamtests_build_corpus` → [`build_corpus.py`](build_corpus.py:1) |
| [`build_corpus_d4j_module`](tests/conftest.py:318) | module | `dynamtests_build_corpus_d4j` → [`build_corpus_d4j.py`](build_corpus_d4j.py:1) |
| [`clean_duplicates_module`](tests/conftest.py:326) | module | `dynamtests_clean_duplicates` → [`clean_duplicates_and_build_dataset.py`](clean_duplicates_and_build_dataset.py:1) |
| [`convert_csv_module`](tests/conftest.py:333) | module | `dynamtests_convert_csv` → [`convert_json_corpus_to_csv_input.py`](convert_json_corpus_to_csv_input.py:1) |

### 5.6 Data builders and hand-written metadata

| Fixture | Scope | Returns |
|---|---|---|
| [`repo_prueba_payload`](tests/conftest.py:343) | session | parsed [`repos_prueba.json`](repos_prueba.json:1) (15 `repo_id`/`url` entries) |
| [`make_mtc_json`](tests/conftest.py:352) | function | [`make_mtc_json()`](tests/fixtures/mining_samples.py:114) builder of synthetic mining JSONs |
| [`make_corpus_record`](tests/conftest.py:360) | function | [`make_corpus_record()`](tests/fixtures/mining_samples.py:161) builder of six-key corpus records |
| [`metadata_focal_context`](tests/conftest.py:475) | function | canonical `{focal_class, focal_method}` dict (TEST_PLAN §C.2) |
| [`metadata_focal_context_no_ext`](tests/conftest.py:483) | function | same, without external dependencies |
| [`metadata_focal_context_no_priv`](tests/conftest.py:491) | function | same, without private members used by the focal method |
| [`metadata_invalid_sig`](tests/conftest.py:499) | function | same, with a class signature that fails validation |
| [`metadata_myclass`](tests/conftest.py:507) | function | metadata of `MyClass.java` (annotated, generic, duplicated imports) |
| [`match_inputs_real`](tests/conftest.py:518) | function | `(test_class, focal_class, test_cases, focal_methods)` parsed with the real parsers |
| [`tmp_log`](tests/conftest.py:556) | function | `io.StringIO()` replacing the `log` file handle of `match_test_cases()` |

### 5.7 Temporary trees (every write stays inside `tmp_path`)

| Fixture | Scope | Returns |
|---|---|---|
| [`java_tmp_tree`](tests/conftest.py:371) | function | `tmp_path/000_java_classes_prueba` with `src/main` + `src/test` copied |
| [`java_tmp_main`](tests/conftest.py:390) | function | its `src/main` |
| [`java_tmp_test`](tests/conftest.py:396) | function | its `src/test` |
| [`all_focal_java_files`](tests/conftest.py:402) | function | the ten `src/main` `.java` files as absolute POSIX paths |
| [`java_main_files`](tests/conftest.py:416) | function | the same files as `Path` objects |
| [`mining_tmp_tree`](tests/conftest.py:425) | function | `tmp_path/mining/{train,validation,test}/output/123/` with two synthetic JSONs per split |
| [`json_corpus_2_repos`](tests/conftest.py:453) | function | `tmp_path/corpus/json/validation/{repoA,repoB}` with one six-key record each |
| [`broken_java_file`](tests/conftest.py:177) | function | `.java` copy of the malformed fixture source inside `tmp_path` |

The e2e module adds one module-scoped fixture of its own,
`pipeline_run`, inside [`tests/e2e/test_mini_pipeline.py`](tests/e2e/test_mini_pipeline.py:1);
shared helpers live in `tests/helpers/`, never as new `conftest.py` fixtures.

---

## 6) `tree-sitter` note: 0.23.2 here vs 0.21.0 pinned in TEST_PLAN

`TEST_PLAN.md` §D.4 targets `tree-sitter==0.21.0` / `tree-sitter-java==0.21.0`;
this machine runs **0.23.2**. The API changed twice:

* `< 0.22.0` → `Language(tsjava.language(), "java")`
* `>= 0.22.0` → `Language(tsjava.language())`
* `< 0.22.1` → `Parser()` + `parser.set_language(lang)`; `>= 0.22.1` → `Parser(lang)`

Both production code ([`ParserUtils.__init__()`](ParserUtils.py:13)) and the test
fixtures ([`java_language`](tests/conftest.py:195),
[`java_parser`](tests/conftest.py:210)) branch on the installed version, so the
suite passes on both lines. Node-level behaviour can still differ: if a literal
pinned from a `< 0.22` run fails here, freeze the observed literal and add the
analytical invariant as a second assertion (the policy already applied by
U-PU-04 and U-FMT-08).

---

## 7) Deliberate strict xfails (`xfail_spoon`) and pinned known bugs

`xfail_spoon` is only a *tag*; the "must stay failing" semantics come from
stacking `@pytest.mark.xfail(strict=True, reason=...)`. If the production code is
fixed without updating the plan and the test, the test **xpasses** and the run
turns red on purpose.

| Id | Contract that must keep failing today | Production site | Desired test |
|---|---|---|---|
| U-MAP-07 | arity/type-aware overload resolution | [`focal_methods_names_norm.index()`](find_map_tests_cases_from_repo.py:614) | [`test_u_map_07_overload_resolution_should_use_arity_and_type`](tests/unit/test_match_test_cases.py:233), [`test_u_map_07_desired_arity_type_aware_overload_resolution`](tests/regression/test_spoon_desired.py:91) |
| U-DUP-04 | skip a record with a `None` body instead of aborting | [`method_src_code + test_src_code`](clean_duplicates_and_build_dataset.py:103) vs the later `None` guard at [`clean_duplicates_and_build_dataset.py:115`](clean_duplicates_and_build_dataset.py:115) | [`test_u_dup_04_extract_uniques_should_ignore_none_test_body`](tests/unit/test_clean_duplicates.py:180), [`test_u_dup_04_desired_skip_none_body_and_keep_valid_record`](tests/regression/test_spoon_desired.py:120) |
| U-CLI-02 | strict boolean parsing | [`type=bool`](build_corpus.py:744) | [`test_u_cli_02_desired_strict_boolean_flag_parsing`](tests/regression/test_spoon_desired.py:157) |

Five xfails are reported in total (the three above plus the mirrored unit
variants of U-MAP-07 and U-DUP-04). Afterwards the whole `xfail_spoon` block can
be deleted in one commit.

### Current behaviour locked by `regression` tests

These are *not* xfails: they pin what the code really does, so an accidental fix
trips an explicit, readable failure.

| Id | Pinned behaviour | Production site | Tests |
|---|---|---|---|
| U-AST-09 | `parse_file()` on a missing path raises `FileNotFoundError` instead of returning `[]` (the `open()` is outside the `try`) | [`ClassParser.py:41`](ClassParser.py:41) | [`test_u_ast_09_missing_file_raises_file_not_found`](tests/unit/test_class_parser.py:191), [`test_u_ast_09_regression_missing_path_propagates_file_not_found`](tests/regression/test_known_bugs.py:90) |
| U-DUP-03 | a `None` body raises `TypeError: can only concatenate str ...` before the `None` filter | [`clean_duplicates_and_build_dataset.py:103`](clean_duplicates_and_build_dataset.py:103) | [`test_u_dup_03_extract_uniques_none_test_body_raises_type_error`](tests/unit/test_clean_duplicates.py:152), [`test_u_dup_03_regression_none_focal_body_aborts_before_none_guard`](tests/regression/test_known_bugs.py:112) |
| U-CLI-01 | `type=bool` turns any non-empty string (`"False"`, `"no"`, `"0"`, a space) into `True` | [`type=bool`](build_corpus.py:744) | [`test_u_cli_01_bool_flag_parsing_keeps_the_type_bool_bug`](tests/unit/test_cli_args.py:61), [`test_u_cli_01_regression_type_bool_coerces_any_non_empty_string`](tests/regression/test_known_bugs.py:145) |
| U-MAP-06 | overloaded focal method names always map to the first declaration (`list.index()`) | [`focal_methods_names_norm.index()`](find_map_tests_cases_from_repo.py:614) | [`test_u_map_06_overloaded_name_match_always_picks_first_declaration`](tests/unit/test_match_test_cases.py:203), [`test_u_map_06_regression_overloaded_names_pick_first_declaration`](tests/regression/test_known_bugs.py:169) |

### Other divergences pinned by the suite (no production change made)

| Id | Plan expected | Observed and pinned |
|---|---|---|
| U-FMT-08 | one space before the class name | [`build_class_signature()`](build_corpus.py:631) rebuilds with a modifier prefix that already ends in a space, so the raw result contains **two** spaces ([`build_corpus.py:645-646`](build_corpus.py:645)); L1/L2/L3 are unaffected because [`clean_tabs_and_new_lines()`](build_corpus.py:661) collapses it — [`test_u_fmt_08_build_class_signature_drops_type_parameters`](tests/unit/test_build_format_corpus.py:325) |
| U-CSV-06 | empty corpus → `pandas.errors.EmptyDataError` | the debug print at [`convert_json_corpus_to_csv_input.py:91`](convert_json_corpus_to_csv_input.py:91) raises `IndexError` first and no CSV is written — [`test_u_csv_06_empty_corpus_raises_index_error_before_writing`](tests/unit/test_convert_csv.py:169) |
| I-01 | `find_map_test_cases(root=…)` with `root` = project folder | `root` must be the **parent** of the project folder, because test paths are normalised with `replace("/src/test/", "/src/main/")` at [`find_map_tests_cases_from_repo.py:289`](find_map_tests_cases_from_repo.py:289); see the module docstring of [`tests/integration/test_find_map_test_cases.py`](tests/integration/test_find_map_test_cases.py:41) |
| E-01 | mining inputs shaped like `mining/{train,validation,test}/output/<repo>/` with two JSONs per split | the e2e module *runs* stage 1 instead of seeding JSONs: it keeps two test methods of `FocalContextTest` and adds `SamePackageExternal01Test` in the tmp copy, so stage 1 exports three mapped cases and the real empty-body filter at [`build_corpus.py:360-364`](build_corpus.py:360) leaves the planned two corpus records — see the module docstring of [`tests/e2e/test_mini_pipeline.py`](tests/e2e/test_mini_pipeline.py:1) |
| E-02 | the session guard patches `git.Repo.clone_from` | GitPython is imported lazily by [`find_map_tests_cases_from_repo.py:22`](find_map_tests_cases_from_repo.py:22), i.e. *after* the session fixture ran, so that particular patch may be absent; E-02 therefore asserts the `socket`/`urllib` guards by using them and proves with a recording stub that [`clone_repo()`](find_map_tests_cases_from_repo.py:82) delegates to `git.Repo.clone_from` and propagates the failure (4 attempts: 1 + 3 retries, sleeps neutralised) |

---

## 8) Hermeticity rules

The suite is meant to run on an offline machine and must never touch research
artefacts:

* **No `.rooignore` path** is read or written: `corpus/`, `dataset/`,
  `defects4j_corpus/`, `repos/`, `mining_results/`, `*.csv`, `*.zip`,
  `*.tar.gz`. [`repos_prueba.json`](repos_prueba.json:1) is the only JSON data
  file the tests read.
* **No network.** [`no_network`](tests/conftest.py:68) is autouse for the whole
  session; no test reaches `find_map_test_cases()`'s clone path, and the `grep`
  subprocess is replaced by a deterministic fake (`find_map_tests_cases_from_repo.py:220`).
* **No absolute machine paths**: everything is created under `tmp_path` /
  `tmp_path_factory`; the only inputs are the repo fixtures
  ([`MyClass.java`](MyClass.java:1), [`000_java_classes_prueba`](000_java_classes_prueba/src/main),
  [`repos_prueba.json`](repos_prueba.json:1), `tests/fixtures/`).
* **No production modification.** If a test surfaces a defect, the test pins the
  observed behaviour (with the reason and the `file:line`) instead of changing
  the pipeline; the fix is tracked by the `xfail_spoon` block.

---

## 9) Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `KeyError: 'GITHUB_USER'` at collection | the script was imported before `tests/conftest.py` ran (e.g. from a plugin or a top-level `import` in a test module). Import production scripts through the module fixtures only. |
| `ModuleNotFoundError: ClassParser` / name clash between `build_corpus` copies | `tests/conftest.py` inserts the repo root and `tests/` in `sys.path` and loads the scripts under aliases (`dynamtests_*`) via [`load_module_from_path()`](tests/helpers/module_loader.py:23); do not `import` them directly. |
| A new test is never selected by `-m unit` | `--strict-markers` is off, so an unknown marker just filters it out. Check the spelling against [`pytest.ini`](pytest.ini:4). |
| `AttributeError` in `Parser()` / `Language()` | mixed `tree-sitter` versions; see §6. |
| `AssertionError: Network access is forbidden …` | a test tried to reach the network or clone a repository — that is the guard working as intended. |
| The e2e block is skipped | the default selection is `-m "not slow"`; the e2e tests are **not** marked `slow`, so this points at an earlier error (check `-m e2e -v`). |
| `xfailed` becomes `failed` | a strict xfail started passing: production behaviour changed. Update `TEST_PLAN.md` and the test (or delete the `xfail_spoon` block) in the same commit. |
