"""Unit tests for the corpus format builders of ``build_corpus.py``.

TEST_PLAN §B.5 -- U-FMT-01 through U-FMT-08 (stage 3: corpus format, levels
L1 / L2 / L3).

Targets
-------
* [`build_format_corpus()`](build_corpus.py:416) -- the single contract that
  produces the three parallel sources of every corpus record.
* [`build_class_signature()`](build_corpus.py:631)
* [`clean_tabs_and_new_lines()`](build_corpus.py:661)

Output levels (TEST_PLAN.md:162-178)
------------------------------------
* **L1** ``src_fm_fc_ms_ff``  -- template at [`build_corpus.py:469`](build_corpus.py:469)
  (``FM_FC_MS_FF``: class signature + body + constructors + public methods +
  public fields).
* **L2** ``src_fm_fc_dctx``    -- template at [`build_corpus.py:599`](build_corpus.py:599)
  (``FM_FC_DCTX``: + private signatures used, ``<FCTX>``/``<ECTX>`` tags).
* **L3** ``src_fm_fc_dctx_priv`` -- template at [`build_corpus.py:613`](build_corpus.py:613)
  (``FM_FC_DCTX`` with the private block wrapped in ``<PRIVATE_FCTX>``).

The three literals are asserted byte-for-byte, as pinned by the foundation
audit; they are never normalised inside the tests.

Known divergence (U-FMT-08)
---------------------------
[`build_class_signature()`](build_corpus.py:631) rebuilds the signature as
``modifiers_and_type + " " + class_name + " " + extends + " " + implements``
([`build_corpus.py:645-646`](build_corpus.py:645)).  ``modifiers_and_type`` is
``class_signature[:class_signature.find(class_name)]`` and therefore already
*ends with a space*, so the rebuilt string contains **two** spaces before the
class name:

    'public class  MyClass extends Parent implements IAction, Clonable'

The TEST_PLAN expected a single space.  This module pins the observed value and
documents it; production code was not modified.  In ``build_format_corpus()``
the artefact is invisible because the whole L1 string is re-normalised by
[`clean_tabs_and_new_lines()`](build_corpus.py:477), which collapses the double
space -- the reason L1..L3 are unaffected.

Module-state isolation
----------------------
``build_corpus.py`` keeps mutable module-level diagnostic lists alive for the
whole pytest process ([`build_corpus.py:40-45`](build_corpus.py:40)).  U-FMT-07
is the only test that appends to ``list_errors_focal_class_sig``; the local
``isolated_class_sig_errors`` fixture swaps the module attribute for a fresh
list (via ``monkeypatch``) and truncates the *original* list back to its
pre-test length in a ``finally`` block, so test order never matters.

Hermetic guarantees
-------------------
No file is written and no socket is opened.  The ``file`` argument of
``build_format_corpus()`` is only interpolated into error messages, so it is
passed as a ``tmp_path``-based label.  ``main()`` is never called: its defaults
point at hard-coded paths ([`build_corpus.py:721-759`](build_corpus.py:721)).
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# L1 / L2 / L3 literals (TEST_PLAN.md:162-178), reproduced byte-for-byte.
# ---------------------------------------------------------------------------
L1_SRC_FM_FC_MS_FF = (
    "public class FocalContext extends Parent implements IAction, Clonable "
    "{ public String doSomething(int val) { return helper(val); } "
    "public FocalContext(); public FocalContext(int val); "
    "public String doSomething(int val); public int counter; }"
)

L2_SRC_FM_FC_DCTX = (
    "<FCTX>public class FocalContext extends Parent implements IAction, Clonable "
    "{ public String doSomething(int val) { return helper(val); } "
    "public FocalContext(); public FocalContext(int val); public int counter; "
    "private int helper(int val); private int secret; }</FCTX> "
    "<ECTX>public class SamePackageExternal01 "
    "{ public String getSomeStrFromSamePackExt01(); }</ECTX>"
)

L3_SRC_FM_FC_DCTX_PRIV = (
    "<FCTX>public class FocalContext extends Parent implements IAction, Clonable "
    "{ public String doSomething(int val) { return helper(val); } "
    "public FocalContext(); public FocalContext(int val); public int counter; "
    "<PRIVATE_FCTX>private int helper(int val); private int secret;</PRIVATE_FCTX> "
    "}</FCTX> "
    "<ECTX>public class SamePackageExternal01 "
    "{ public String getSomeStrFromSamePackExt01(); }</ECTX>"
)


# ---------------------------------------------------------------------------
# Local helpers / fixtures (module-private; nothing is added to conftest.py)
# ---------------------------------------------------------------------------
def _build_format_corpus(module, parser_utils, metadata, file_label):
    """Call ``build_format_corpus`` with the default tags on ``metadata``.

    The ``focal_method['body']`` is used as ``body_method``, matching the
    call site at [`build_corpus.py:396-402`](build_corpus.py:396).
    """
    focal_class = metadata["focal_class"]
    focal_method = metadata["focal_method"]
    return module.build_format_corpus(
        parser_utils,
        focal_class,
        focal_method,
        focal_method["body"],
        TAG_FOCTX_START,
        TAG_FOCTX_END,
        TAG_ECTX_START,
        TAG_ECTX_END,
        TAG_PRIV_START,
        TAG_PRIV_END,
        file_label,
    )


@pytest.fixture
def isolated_class_sig_errors(build_corpus_module, monkeypatch):
    """Serve a fresh ``list_errors_focal_class_sig`` and restore the baseline.

    The module-level list at [`build_corpus.py:42`](build_corpus.py:42) survives
    across tests in the same process.  The fixture (1) records the original
    length, (2) replaces the module attribute with a brand-new list so the test
    starts from a known ``[]``, and (3) on teardown truncates the *original*
    list back to the recorded baseline, leaving the process as it was found.
    """
    original_list = build_corpus_module.list_errors_focal_class_sig
    baseline_len = len(original_list)

    fresh_list = []
    monkeypatch.setattr(
        build_corpus_module, "list_errors_focal_class_sig", fresh_list
    )
    try:
        yield fresh_list
    finally:
        del original_list[baseline_len:]


# ---------------------------------------------------------------------------
# U-FMT-01 -- L1: src_fm_fc_ms_ff matches the template at build_corpus.py:469
# ---------------------------------------------------------------------------
def test_u_fmt_01_src_fm_fc_ms_ff_literal_l1(
    build_corpus_module, parser_utils, metadata_focal_context, tmp_path
):
    result = _build_format_corpus(
        build_corpus_module,
        parser_utils,
        metadata_focal_context,
        str(tmp_path / "FocalContext_0.json"),
    )

    assert isinstance(result, tuple) and len(result) == 3
    src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv = result

    # L1 -- FM_FC_MS_FF: no context tags at all.
    assert src_fm_fc_ms_ff == L1_SRC_FM_FC_MS_FF
    assert "<FCTX>" not in src_fm_fc_ms_ff
    assert "<ECTX>" not in src_fm_fc_ms_ff

    # Guard against accidental tag/level swapping between the three outputs.
    assert src_fm_fc_dctx != src_fm_fc_ms_ff
    assert src_fm_fc_dctx_priv != src_fm_fc_dctx


# ---------------------------------------------------------------------------
# U-FMT-02 -- L2: src_fm_fc_dctx matches the template at build_corpus.py:599
# ---------------------------------------------------------------------------
def test_u_fmt_02_src_fm_fc_dctx_literal_l2(
    build_corpus_module, parser_utils, metadata_focal_context, tmp_path
):
    _l1, src_fm_fc_dctx, _l3 = _build_format_corpus(
        build_corpus_module,
        parser_utils,
        metadata_focal_context,
        str(tmp_path / "FocalContext_0.json"),
    )

    # L2 -- FM_FC_DCTX: private signatures inline, external context in <ECTX>.
    assert src_fm_fc_dctx == L2_SRC_FM_FC_DCTX
    assert "private int helper(int val); private int secret;" in src_fm_fc_dctx
    # The private block is not tagged in the L2 variant (that is L3 only).
    assert TAG_PRIV_START not in src_fm_fc_dctx


# ---------------------------------------------------------------------------
# U-FMT-03 -- L3: src_fm_fc_dctx_priv matches the template at build_corpus.py:613
# ---------------------------------------------------------------------------
def test_u_fmt_03_src_fm_fc_dctx_priv_literal_l3(
    build_corpus_module, parser_utils, metadata_focal_context, tmp_path
):
    _l1, _l2, src_fm_fc_dctx_priv = _build_format_corpus(
        build_corpus_module,
        parser_utils,
        metadata_focal_context,
        str(tmp_path / "FocalContext_0.json"),
    )

    # L3 -- FM_FC_DCTX_PRIV: the private block is wrapped by <PRIVATE_FCTX>.
    assert src_fm_fc_dctx_priv == L3_SRC_FM_FC_DCTX_PRIV
    assert (
        TAG_PRIV_START + "private int helper(int val); private int secret;" + TAG_PRIV_END
    ) in src_fm_fc_dctx_priv


# ---------------------------------------------------------------------------
# U-FMT-04 -- empty external context: build_corpus.py:565-566
# ---------------------------------------------------------------------------
def test_u_fmt_04_empty_external_context_branch(
    build_corpus_module, parser_utils, metadata_focal_context_no_ext, tmp_path
):
    _l1, src_fm_fc_dctx, _l3 = _build_format_corpus(
        build_corpus_module,
        parser_utils,
        metadata_focal_context_no_ext,
        str(tmp_path / "FocalContext_1.json"),
    )

    # No dependencies -> a single empty pair of tags, not an omitted block.
    assert src_fm_fc_dctx.endswith("</FCTX> <ECTX></ECTX>")
    assert src_fm_fc_dctx.count(TAG_ECTX_START) == 1
    assert src_fm_fc_dctx.count(TAG_ECTX_END) == 1


# ---------------------------------------------------------------------------
# U-FMT-05 -- empty private block: build_corpus.py:619
# ---------------------------------------------------------------------------
def test_u_fmt_05_empty_private_context_branch(
    build_corpus_module, parser_utils, metadata_focal_context_no_priv, tmp_path
):
    _l1, src_fm_fc_dctx, src_fm_fc_dctx_priv = _build_format_corpus(
        build_corpus_module,
        parser_utils,
        metadata_focal_context_no_priv,
        str(tmp_path / "FocalContext_2.json"),
    )

    # L3 always emits the tag pair, even when the private block is empty.
    assert "<PRIVATE_FCTX></PRIVATE_FCTX>" in src_fm_fc_dctx_priv
    # L2 never emits the private tag, empty or not.
    assert TAG_PRIV_START not in src_fm_fc_dctx
    assert TAG_PRIV_END not in src_fm_fc_dctx
    # Everything else (public members + external context) is unchanged.
    assert src_fm_fc_dctx == (
        "<FCTX>public class FocalContext extends Parent implements IAction, Clonable "
        "{ public String doSomething(int val) { return helper(val); } "
        "public FocalContext(); public FocalContext(int val); public int counter; }"
        "</FCTX> <ECTX>public class SamePackageExternal01 "
        "{ public String getSomeStrFromSamePackExt01(); }</ECTX>"
    )


# ---------------------------------------------------------------------------
# U-FMT-06 -- clean_tabs_and_new_lines(): collapse + strip + idempotence
# ---------------------------------------------------------------------------
def test_u_fmt_06_clean_tabs_and_new_lines(build_corpus_module):
    clean = build_corpus_module.clean_tabs_and_new_lines

    # Newlines/tabs -> space, then any run of 2+ spaces -> one space, then strip.
    assert clean("  a\n\tb   c  ") == "a b c"

    # Idempotence: f(f(x)) == f(x) for a representative input.
    x = " a\n\tb  c "
    once = clean(x)
    assert once == "a b c"
    assert clean(once) == once

    # Edge: already normalised text is returned untouched.
    assert clean("public class X { }") == "public class X { }"


# ---------------------------------------------------------------------------
# U-FMT-07 -- class-signature validation failure: build_corpus.py:440-446
# ---------------------------------------------------------------------------
def test_u_fmt_07_class_signature_validation_failure_returns_none_triplet(
    build_corpus_module,
    parser_utils,
    metadata_invalid_sig,
    isolated_class_sig_errors,
    monkeypatch,
    tmp_path,
):
    # Force the validation to report an error for *every* snippet, so the very
    # first check (class signature) at build_corpus.py:439-446 aborts.
    monkeypatch.setattr(
        parser_utils, "validate_if_code_has_errors", lambda *args, **kwargs: True
    )

    file_label = str(tmp_path / "invalid_sig_0.json")
    result = _build_format_corpus(
        build_corpus_module, parser_utils, metadata_invalid_sig, file_label
    )

    # Tuple unpacking at the call site expects three elements (all None).
    assert result == (None, None, None)
    assert len(isolated_class_sig_errors) == 1

    # The single entry records the offending file and the rebuilt signature.
    message = isolated_class_sig_errors[0]
    assert message.startswith("File error Class Signature: ")
    assert file_label in message


# ---------------------------------------------------------------------------
# U-FMT-08 -- build_class_signature(): drops <T>, re-adds extends/implements
# ---------------------------------------------------------------------------
@pytest.mark.regression
def test_u_fmt_08_build_class_signature_drops_type_parameters(
    build_corpus_module, parser_utils, metadata_myclass
):
    focal_class = metadata_myclass["focal_class"]

    signature = build_corpus_module.build_class_signature(parser_utils, focal_class)

    # Documented divergence (see module docstring): the modifiers prefix already
    # ends with a space, so the rebuild at build_corpus.py:645-646 yields a
    # double space before the class name.  Pinned as observed.
    assert signature == "public class  MyClass extends Parent implements IAction, Clonable"

    # Behaviour the plan calls out as pinned:
    assert "<T>" not in signature, "build_class_signature must drop type parameters"
    assert "@AllConstructors" not in signature
    assert signature.endswith("extends Parent implements IAction, Clonable")
    assert signature.startswith("public class")
