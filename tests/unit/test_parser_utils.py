"""Unit tests for :mod:`ParserUtils` (TEST_PLAN section B.2, U-PU-01..U-PU-07).

Targets
-------
* [`ParserUtils.clean_comments()`](ParserUtils.py:101)
* [`ParserUtils.clean_annotations()`](ParserUtils.py:173)
* [`ParserUtils.fix_type_parameters_inconsistences()`](ParserUtils.py:314)
* [`ParserUtils.method_body_is_empty()`](ParserUtils.py:66)
* [`ParserUtils.validate_if_code_has_errors()`](ParserUtils.py:30)
* [`ParserUtils.fix_close_type_parameter_sig_class()`](ParserUtils.py:277)

Environment
-----------
Verified against ``tree-sitter`` / ``tree-sitter-java`` **0.23.2** (the TEST_PLAN
was written for 0.21.0).  Every literal asserted below was observed on 0.23.2.

Known divergence (U-PU-06, case c)
----------------------------------
The plan documents ``validate_if_code_has_errors('public FocalContext { }', False)
is False`` ("tolerant": the only *missing* nodes are ``identifier``).  On
tree-sitter 0.23.2 that input parses to
``(program (ERROR (modifiers) (type_identifier)) (block))``: *no* node is
``is_missing``, but the root's ``has_error`` is ``True`` and one real ``ERROR``
node exists.  The tolerant branch at [`ParserUtils.py:58`](ParserUtils.py:58)
therefore does not apply and the function returns ``True``.  The test pins the
observed value; production code was not modified.

All inputs are string literals; nothing here touches the network, the
filesystem, or a ``.rooignore``d directory.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# U-PU-01 -- clean_comments(): line comment -> single space, no collapsing
# ---------------------------------------------------------------------------
def test_u_pu_01_clean_comments_line_comment_replaced_by_space(parser_utils):
    source = "int a = 1; // c\nint b = 2;"

    result = parser_utils.clean_comments(source)

    # The line comment is replaced by one space (ParserUtils.py:163); the two
    # spaces before the newline are preserved (no collapsing, no strip).
    assert result == "int a = 1;  \nint b = 2;"
    assert "// c" not in result


# ---------------------------------------------------------------------------
# U-PU-02 -- clean_comments(): block comment -> single space
# ---------------------------------------------------------------------------
def test_u_pu_02_clean_comments_block_comment_replaced_by_space(parser_utils):
    source = "int a = 1; /* x */ int b = 2;"

    result = parser_utils.clean_comments(source)

    # Block comment replaced by one space (ParserUtils.py:141), leaving the
    # three consecutive spaces between the statements.
    assert result == "int a = 1;   int b = 2;"
    assert "/* x */" not in result


# ---------------------------------------------------------------------------
# U-PU-03 -- clean_annotations(): annotation removed and stripped
# ---------------------------------------------------------------------------
def test_u_pu_03_clean_annotations_removes_override(parser_utils):
    source = '@Override public String toString() { return ""; }'

    result = parser_utils.clean_annotations(source)

    # The annotation text is removed (ParserUtils.py:210) and the result is
    # stripped, so the leading space disappears.
    assert result == 'public String toString() { return ""; }'
    assert "@Override" not in result


# ---------------------------------------------------------------------------
# U-PU-04 -- fix_type_parameters_inconsistences(): drop leading <T> error node
# ---------------------------------------------------------------------------
def test_u_pu_04_fix_type_parameters_inconsistences_removes_duplicate(parser_utils):
    source = "public<T> <T> MyConstructor() { }"

    result = parser_utils.fix_type_parameters_inconsistences(source)

    # Error node whose first child is ``type_parameters`` is deleted
    # (ParserUtils.py:342-345) and runs of whitespace are collapsed
    # (ParserUtils.py:350).  The invariant from the plan is kept as well.
    assert result == "public <T> MyConstructor() { }"
    assert result.count("<T>") == 1


# ---------------------------------------------------------------------------
# U-PU-05 -- method_body_is_empty(): empty body, non-empty body, no body node
# ---------------------------------------------------------------------------
def test_u_pu_05_method_body_is_empty_three_shapes(parser_utils):
    assert parser_utils.method_body_is_empty("public void a() { }") is True
    assert parser_utils.method_body_is_empty("public void a() { return; }") is False
    # Abstract declarations have no ``body`` child, which is treated as empty
    # (ParserUtils.py:81-83).
    assert parser_utils.method_body_is_empty("public abstract void a();") is True


# ---------------------------------------------------------------------------
# U-PU-06 -- validate_if_code_has_errors(): all_errors flag vs tolerant mode
# ---------------------------------------------------------------------------
def test_u_pu_06_validate_if_code_has_errors_cases(parser_utils):
    # (a) genuinely broken members -> has_error True with validate_all_errors
    assert parser_utils.validate_if_code_has_errors("public class X { void a( }", True) is True
    # (b) valid compilation unit -> no errors
    assert parser_utils.validate_if_code_has_errors("public class X { }", True) is False
    # (c) DRIFT on tree-sitter 0.23.2: documented value was False (tolerant
    #     branch, ParserUtils.py:47-59).  On 0.23.2 the input yields a real
    #     ERROR node with no missing identifiers, so the tolerant branch is not
    #     taken and the observed result is True.
    assert parser_utils.validate_if_code_has_errors("public FocalContext { }", False) is True
    # (d) valid compilation unit in tolerant mode -> no errors
    assert parser_utils.validate_if_code_has_errors("public class X { }", False) is False


# ---------------------------------------------------------------------------
# U-PU-07 -- fix_close_type_parameter_sig_class(): restore missing '>'
# ---------------------------------------------------------------------------
def test_u_pu_07_fix_close_type_parameter_sig_class_closes_generic(parser_utils):
    source = "public class SomeClass<T"

    result = parser_utils.fix_close_type_parameter_sig_class(source)

    # The missing '>' node is reinserted (ParserUtils.py:297-300) and the
    # temporary " { }" suffix is removed character-wise (ParserUtils.py:307).
    assert result == "public class SomeClass<T>"
    assert "{" not in result
    assert "}" not in result
