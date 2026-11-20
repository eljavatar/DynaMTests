"""Parity contract between ``build_corpus.py`` and ``build_corpus_d4j.py``.

TEST_PLAN §B.8 — U-PAR-01 through U-PAR-03 (stage 6: Defects4J corpus).

Targets
-------
* [`build_format_corpus()`](build_corpus.py:416) vs
  [`build_format_corpus()`](build_corpus_d4j.py:375)
* [`build_class_signature()`](build_corpus.py:631) vs
  [`build_class_signature()`](build_corpus_d4j.py:577)

``build_corpus_d4j.py`` is a copy of stage-3 code from ``build_corpus.py``
(TEST_PLAN obstacle O8).  Both files declare *identically named* functions, so
they are loaded **only** through the aliased fixtures ``build_corpus_module``
(alias ``dynamtests_build_corpus``) and ``build_corpus_d4j_module`` (alias
``dynamtests_build_corpus_d4j``).  A plain ``import build_corpus`` would produce
a module compared against itself and make every parity assertion vacuous.

Observed parity relationship (measured on this checkout, Python 3.9.13)
----------------------------------------------------------------------
``build_format_corpus``
    * Structurally **identical**: ``ast.dump`` of both bodies is equal after
      ``textwrap.dedent`` and docstring stripping, with
      ``include_attributes=False`` (so line numbers do not participate).
    * The raw sources are **not** byte-identical.  Every differing line is a
      comment or a blank line
      ([`build_corpus.py:427`](build_corpus.py:427) "# ADD static_initializer
      from mining: For next version", the alternative commented-out
      implementation at [`build_corpus.py:570-585`](build_corpus.py:570) versus
      [`build_corpus_d4j.py:516-532`](build_corpus_d4j.py:516), and a mislabelled
      comment at [`build_corpus.py:502`](build_corpus.py:502) "# Extract all
      public constructors" versus
      [`build_corpus_d4j.py:454`](build_corpus_d4j.py:454) "# Extract all private
      constructors" — the *code* below both comments is the same and correct).
    * Runtime behaviour is identical: the returned ``(src_fm_fc_ms_ff,
      src_fm_fc_dctx, src_fm_fc_dctx_priv)`` triplet is equal for all three
      metadata variants exercised by this module.

``build_class_signature``
    * Structurally **and** textually identical
      ([`build_corpus.py:631-652`](build_corpus.py:631) versus
      [`build_corpus_d4j.py:577-598`](build_corpus_d4j.py:577)).

Because the two implementations do not legitimately differ, U-PAR-03 asserts
full ``ast.dump`` equality.  The guard ignores comments on purpose: the
complementary "significant source lines" check strips ``#`` lines so that
comment-only edits never turn the suite red, while any added/removed *code* in
one copy fails with a unified diff naming the drifted function.

Documented TEST_PLAN gap (U-PAR-02)
-----------------------------------
TEST_PLAN §B.8 expects ``'public class MyClass extends Parent implements
IAction, Clonable'`` (one space).  Both copies actually return **two** spaces:
``format_class_signature = '{} {} {} {}'`` is fed a ``modifiers_and_type``
prefix that already ends with a space
([`build_corpus.py:644-646`](build_corpus.py:644),
[`build_corpus_d4j.py:590-592`](build_corpus_d4j.py:590)).  Parity therefore
holds, but the plan literal is unattainable; the observed value is pinned and
documented instead (same artefact as U-FMT-08 in
[`tests/unit/test_build_format_corpus.py`](tests/unit/test_build_format_corpus.py:26)).
Production code was not modified.

Module-state isolation
----------------------
Both modules keep mutable module-level diagnostic lists alive for the whole
pytest process ([`build_corpus.py:40-45`](build_corpus.py:40),
[`build_corpus_d4j.py:12-16`](build_corpus_d4j.py:12)).  ``build_format_corpus``
appends to them on every validation failure, so the
``isolated_module_diagnostics`` fixture swaps **every** ``list_errors_*``
attribute of **both** modules for a fresh list (via ``monkeypatch``) and, on
teardown, truncates the *original* lists back to the length they had when the
test started.  Test order never matters and no entry leaks into other modules.

Hermetic guarantees
-------------------
Nothing is written: ``build_format_corpus`` only interpolates its ``file``
argument into error messages, therefore a ``tmp_path``-based label is passed and
``tmp_path`` is asserted to stay empty.  ``build_corpus()`` /
``build_corpus_d4j()`` (the functions that create ``json/`` and ``raw/``
directories, [`build_corpus.py:98-102`](build_corpus.py:98)) are never called.
No socket is opened (the autouse ``no_network`` fixture stays in force) and no
``.rooignore`` path (``corpus/``, ``dataset/``, ``defects4j_corpus/``,
``repos/``) is touched.
"""

from __future__ import annotations

import ast
import copy
import difflib
import inspect
import textwrap

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Default tags (mirrors the CLI defaults pinned by U-CLI-03, build_corpus.py:760)
# ---------------------------------------------------------------------------
TAG_FOCTX_START = "<FCTX>"
TAG_FOCTX_END = "</FCTX>"
TAG_ECTX_START = "<ECTX>"
TAG_ECTX_END = "</ECTX>"
TAG_PRIV_START = "<PRIVATE_FCTX>"
TAG_PRIV_END = "</PRIVATE_FCTX>"

TAGS = (
    TAG_FOCTX_START,
    TAG_FOCTX_END,
    TAG_ECTX_START,
    TAG_ECTX_END,
    TAG_PRIV_START,
    TAG_PRIV_END,
)

# The three metadata variants required by TEST_PLAN §B.8 for U-PAR-01.
METADATA_FIXTURES = (
    "metadata_focal_context",
    "metadata_focal_context_no_ext",
    "metadata_focal_context_no_priv",
)

# Observed value (see module docstring): two spaces before the class name, in
# both copies.  TEST_PLAN expected a single space; the plan literal is a gap.
EXPECTED_MYCLASS_SIGNATURE = (
    "public class  MyClass extends Parent implements IAction, Clonable"
)


# ---------------------------------------------------------------------------
# Local helpers (module-private; nothing is added to conftest.py)
# ---------------------------------------------------------------------------
def _build_format_corpus(module, parser_utils, metadata, file_label):
    """Call ``module.build_format_corpus`` with the default tags.

    ``focal_method['body']`` is passed as ``body_method``, exactly like the
    production call site ([`build_corpus.py:396-402`](build_corpus.py:396)).
    The very same ``metadata`` object is handed to both modules so that the
    comparison also proves the functions are side-effect free on their inputs.
    """
    focal_class = metadata["focal_class"]
    focal_method = metadata["focal_method"]
    return module.build_format_corpus(
        parser_utils,
        focal_class,
        focal_method,
        focal_method["body"],
        *TAGS,
        file_label,
    )


def _function_ast(func) -> ast.AST:
    """Return the AST of *func*, dedented and without a leading docstring.

    ``inspect.getsource`` keeps the original indentation only for nested
    functions; ``textwrap.dedent`` makes the helper safe for both cases.  The
    docstring is dropped defensively: documenting one copy only must not read as
    structural drift.
    """
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)
    function_def = tree.body[0]
    body = getattr(function_def, "body", [])
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        function_def.body = body[1:] or [ast.Pass()]
    return tree


def _normalised_ast_dump(func) -> str:
    """Canonical structural fingerprint: no line numbers, no comments, no docs."""
    return ast.dump(_function_ast(func), include_attributes=False)


def _statement_count(func) -> int:
    """Number of ``ast.stmt`` nodes: proves the comparison is non-trivial."""
    return sum(1 for node in ast.walk(_function_ast(func)) if isinstance(node, ast.stmt))


def _significant_source_lines(func):
    """Source lines of *func* with comments and blank lines removed.

    Used as the "comments are the only textual difference" guard: it is
    deliberately blind to ``#`` comments so that a comment-only edit in either
    copy never fails the suite.
    """
    lines = []
    for raw_line in textwrap.dedent(inspect.getsource(func)).splitlines():
        stripped = raw_line.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def _unified_line_diff(left, right, left_name, right_name) -> str:
    return "\n".join(
        difflib.unified_diff(
            left,
            right,
            fromfile=left_name,
            tofile=right_name,
            lineterm="",
            n=2,
        )
    )


# ---------------------------------------------------------------------------
# Diagnostics isolation for BOTH modules
# ---------------------------------------------------------------------------
@pytest.fixture
def isolated_module_diagnostics(
    build_corpus_module, build_corpus_d4j_module, monkeypatch
):
    """Swap every ``list_errors_*`` of both modules for a fresh list.

    Yields ``{(module_label, attribute_name): fresh_list}`` so a test can assert
    that *no* diagnostic was recorded.  On teardown the original lists (which
    survive for the whole pytest process) are truncated back to the length they
    had when the test started, leaving the process exactly as it was found.
    """
    originals = {}
    fresh_lists = {}

    modules = (
        ("build_corpus", build_corpus_module),
        ("build_corpus_d4j", build_corpus_d4j_module),
    )

    for module_label, module in modules:
        diagnostic_names = sorted(
            name for name in vars(module) if name.startswith("list_errors_")
        )
        assert diagnostic_names, (
            f"{module_label} no longer exposes list_errors_* diagnostics; "
            "update this fixture together with the production module."
        )
        for name in diagnostic_names:
            original_list = getattr(module, name)
            baseline_len = len(original_list)
            replacement = []
            monkeypatch.setattr(module, name, replacement)
            originals[(module_label, name)] = (original_list, baseline_len)
            fresh_lists[(module_label, name)] = replacement

    try:
        yield fresh_lists
    finally:
        for original_list, baseline_len in originals.values():
            del original_list[baseline_len:]


# ---------------------------------------------------------------------------
# U-PAR-01 — same triplet for build_format_corpus in both modules
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("metadata_fixture_name", METADATA_FIXTURES)
def test_u_par_01_build_format_corpus_triplet_parity(
    build_corpus_module,
    build_corpus_d4j_module,
    parser_utils,
    isolated_module_diagnostics,
    request,
    metadata_fixture_name,
    tmp_path,
):
    """`build_format_corpus` returns the same triplet from both modules.

    Same dict instance, same ``ParserUtils`` instance, same tags, same
    ``file`` label; the full tuple is compared, not only element 0.
    """
    metadata = request.getfixturevalue(metadata_fixture_name)
    metadata_snapshot = copy.deepcopy(metadata)
    file_label = str(tmp_path / f"parity_{metadata_fixture_name}.json")

    triplet_build_corpus = _build_format_corpus(
        build_corpus_module, parser_utils, metadata, file_label
    )
    triplet_d4j = _build_format_corpus(
        build_corpus_d4j_module, parser_utils, metadata, file_label
    )

    # Contract shape first, so an implementation returning an early ``None``
    # tuple is reported as such instead of as a confusing equality failure.
    assert isinstance(triplet_build_corpus, tuple)
    assert isinstance(triplet_d4j, tuple)
    assert len(triplet_build_corpus) == 3
    assert len(triplet_d4j) == 3
    assert all(part is not None for part in triplet_build_corpus), (
        f"build_corpus.build_format_corpus returned a None entry for "
        f"{metadata_fixture_name}: {triplet_build_corpus!r}"
    )
    assert all(part is not None for part in triplet_d4j), (
        f"build_corpus_d4j.build_format_corpus returned a None entry for "
        f"{metadata_fixture_name}: {triplet_d4j!r}"
    )

    # L1 / L2 / L3 -- whole-tuple parity.
    assert triplet_build_corpus == triplet_d4j

    # Element-wise parity, kept explicit for a readable failure message.
    for index, (part_build_corpus, part_d4j) in enumerate(
        zip(triplet_build_corpus, triplet_d4j)
    ):
        assert part_build_corpus == part_d4j, (
            f"element {index} drifted for {metadata_fixture_name}"
        )

    # No validation-failure path was taken: the file label only appears in
    # diagnostic messages, never in the produced sources.
    for part in triplet_build_corpus:
        assert file_label not in part

    # Both modules kept their diagnostics untouched (proves the equality above
    # was not produced by two *identical failures* returning None triplets).
    for (module_label, attribute_name), fresh_list in (
        isolated_module_diagnostics.items()
    ):
        assert fresh_list == [], (
            f"{module_label}.{attribute_name} recorded {fresh_list!r} for "
            f"{metadata_fixture_name}"
        )

    # The input dictionaries are read-only for both implementations.
    assert metadata == metadata_snapshot

    # Hermetic: the ``file`` argument is a label only, nothing was written.
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# U-PAR-02 — same class signature for build_class_signature in both modules
# ---------------------------------------------------------------------------
def test_u_par_02_build_class_signature_parity(
    build_corpus_module, build_corpus_d4j_module, parser_utils, metadata_myclass
):
    """`build_class_signature` agrees with itself across the two copies.

    TEST_PLAN expected ``'public class MyClass extends Parent implements IAction,
    Clonable'``.  Both copies actually emit a double space (see module
    docstring); parity is what this test owns, and the observed literal is
    pinned with the gap documented.
    """
    class_dict = metadata_myclass["focal_class"]

    signature_build_corpus = build_corpus_module.build_class_signature(
        parser_utils, class_dict
    )
    signature_d4j = build_corpus_d4j_module.build_class_signature(
        parser_utils, class_dict
    )

    assert signature_build_corpus == signature_d4j

    # Observed value in both copies: two spaces before the class name
    # (build_corpus.py:644-646 / build_corpus_d4j.py:590-592).
    assert signature_build_corpus == EXPECTED_MYCLASS_SIGNATURE
    assert signature_d4j == EXPECTED_MYCLASS_SIGNATURE

    # Behaviour shared by both copies (mirrors U-FMT-08).
    for signature in (signature_build_corpus, signature_d4j):
        assert "<T>" not in signature
        assert "@AllConstructors" not in signature
        assert signature.startswith("public class")
        assert signature.endswith("extends Parent implements IAction, Clonable")


# ---------------------------------------------------------------------------
# U-PAR-03 — source-AST drift guard
# ---------------------------------------------------------------------------
def test_u_par_03_build_format_corpus_ast_drift_guard(
    build_corpus_module, build_corpus_d4j_module
):
    """Structural fingerprint of the duplicated functions must not drift.

    For each duplicated function the guard asserts:

    1. the normalised ``ast.dump`` (dedented, docstring stripped,
       ``include_attributes=False``) is equal -- comments and line numbers are
       invisible, so a comment-only edit never fails;
    2. the comment/blank-line-stripped source lines are equal -- the observed
       relationship is "identical code, comments are the only textual
       difference" for ``build_format_corpus`` and "byte-identical source" for
       ``build_class_signature``;
    3. the statement counts are equal and non-trivial, so an accidentally
       emptied or stubbed copy cannot pass.

    ``build_corpus_d4j`` may legitimately lag behind ``build_corpus`` in later
    stages; when that happens this guard must be updated *together* with the
    lagging copy and the divergence documented here with ``file:line``.
    """
    duplicated_functions = ("build_format_corpus", "build_class_signature")
    problems = []

    for function_name in duplicated_functions:
        func_build_corpus = getattr(build_corpus_module, function_name)
        func_d4j = getattr(build_corpus_d4j_module, function_name)

        dump_build_corpus = _normalised_ast_dump(func_build_corpus)
        dump_d4j = _normalised_ast_dump(func_d4j)

        statements_build_corpus = _statement_count(func_build_corpus)
        statements_d4j = _statement_count(func_d4j)

        if statements_build_corpus < 3:
            problems.append(
                f"{function_name}: build_corpus copy has only "
                f"{statements_build_corpus} statements (suspiciously empty)"
            )
        if statements_d4j != statements_build_corpus:
            problems.append(
                f"{function_name}: statement count drifted "
                f"(build_corpus={statements_build_corpus}, "
                f"build_corpus_d4j={statements_d4j})"
            )

        if dump_build_corpus != dump_d4j:
            problems.append(
                f"{function_name}: ast.dump drifted\n"
                + _unified_line_diff(
                    _significant_source_lines(func_build_corpus),
                    _significant_source_lines(func_d4j),
                    "build_corpus.py",
                    "build_corpus_d4j.py",
                )
            )

        # Comments and blank lines are the only tolerated textual difference.
        assert _significant_source_lines(func_build_corpus) == (
            _significant_source_lines(func_d4j)
        ), (
            f"{function_name}: sources differ beyond comments/blank lines\n"
            + _unified_line_diff(
                _significant_source_lines(func_build_corpus),
                _significant_source_lines(func_d4j),
                "build_corpus.py",
                "build_corpus_d4j.py",
            )
        )

    assert not problems, "\n\n".join(problems)

    # Non-triviality of the compared bodies, pinned loosely on purpose: the
    # guard must survive cosmetic edits but not a replacement by a stub.
    assert _statement_count(build_corpus_module.build_format_corpus) >= 50
    assert _statement_count(build_corpus_module.build_class_signature) >= 10
