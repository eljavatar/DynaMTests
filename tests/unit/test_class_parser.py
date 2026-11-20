"""Unit tests for :mod:`ClassParser` (TEST_PLAN section B.1, U-AST-01..U-AST-09).

Targets
-------
* [`ClassParser.parse_file()`](ClassParser.py:32)
* [`ClassParser.get_class_metadata()`](ClassParser.py:300)
* [`ClassParser.get_class_fields()`](ClassParser.py:368)
* [`ClassParser.get_function_metadata()`](ClassParser.py:443)
* [`ClassParser.get_static_imports()`](ClassParser.py:1542)
* [`ClassParser.get_class_imports()`](ClassParser.py:1561)

Environment
-----------
Verified against ``tree-sitter`` / ``tree-sitter-java`` 0.23.2 (the TEST_PLAN was
written for 0.21.0).  Every literal asserted below was observed on 0.23.2, so no
expectation from section B.1 had to be re-pinned.

Testability note (obstacle O6)
------------------------------
[`ClassParser.py:41`](ClassParser.py:41) opens the file *outside* the ``try``
block, so a missing path propagates ``FileNotFoundError`` instead of returning
``[]``.  ``U-AST-09`` pins that real behaviour without touching production code.

All inputs are read-only repository fixtures or ``tmp_path`` copies; nothing here
touches the network or a ``.rooignore``d directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ``java_tmp_tree`` copies ``000_java_classes_prueba/src/{main,test}`` into
# ``tmp_path``; paths below are composed from the existing ``java_tmp_main``
# fixture (no fixture logic is duplicated here).
FOCAL_CONTEXT_RELATIVE_PATH = Path("com") / "eljavatar" / "focals" / "FocalContext.java"


def _focal_context_classes(class_parser, java_tmp_main: Path):
    """Parse ``FocalContext.java`` from the temporary tree and return its classes."""
    return class_parser.parse_file(str(java_tmp_main / FOCAL_CONTEXT_RELATIVE_PATH))


# ---------------------------------------------------------------------------
# U-AST-01 -- parse_file() extracts every top-level class of the file
# ---------------------------------------------------------------------------
def test_u_ast_01_parse_file_extracts_classes(class_parser, java_tmp_main):
    classes = _focal_context_classes(class_parser, java_tmp_main)

    assert len(classes) == 3
    assert [c["class_name"] for c in classes] == [
        "FocalContext",
        "ExternalContext04",
        "ExternalContext04Test",
    ]


# ---------------------------------------------------------------------------
# U-AST-02 -- get_class_metadata(): package, imports, header, signature
# ---------------------------------------------------------------------------
def test_u_ast_02_focal_context_class_metadata(class_parser, java_tmp_main):
    classes = _focal_context_classes(class_parser, java_tmp_main)
    focal_class = next(c for c in classes if c["class_name"] == "FocalContext")

    assert focal_class["class_name"] == "FocalContext"
    assert focal_class["package"] == "package com.eljavatar.focals;"
    assert len(focal_class["imports"]) == 9
    assert focal_class["has_constructor"] is True
    assert focal_class["superclass"] == "extends Parent"
    assert focal_class["interfaces"] == "implements IAction, Clonable"
    assert (
        focal_class["class_signature"]
        == "public class FocalContext extends Parent implements IAction, Clonable"
    )


# ---------------------------------------------------------------------------
# U-AST-03 -- get_class_fields() over the real class node
# ---------------------------------------------------------------------------
def test_u_ast_03_get_class_fields(class_parser, java_tmp_main, parse_java_source):
    source = (java_tmp_main / FOCAL_CONTEXT_RELATIVE_PATH).read_text(encoding="utf-8")
    tree = parse_java_source(source)
    class_node = next(
        node for node in tree.root_node.children if node.type == "class_declaration"
    )

    fields = class_parser.get_class_fields(class_node, source)

    assert [(f["var_name"], f["type"], f["modifier"]) for f in fields] == [
        ("ext01", "ExternalContext01", "private"),
        ("fromSamePackExt01", "SamePackageExternal01", "private"),
    ]


# ---------------------------------------------------------------------------
# U-AST-04 -- parse_file(): method names and parameter arity, in source order
# ---------------------------------------------------------------------------
def test_u_ast_04_methods_name_and_arity(class_parser, java_tmp_main):
    classes = _focal_context_classes(class_parser, java_tmp_main)
    focal_class = next(c for c in classes if c["class_name"] == "FocalContext")

    assert [
        (m["method_name"], len(m["parameters_list"])) for m in focal_class["methods"]
    ] == [
        ("FocalContext", 0),
        ("FocalContext", 1),
        ("doSomething", 5),
        ("callSomeMethod", 1),
        ("runSomeVoid", 1),
        ("runSomeVoid", 1),
        ("runSomeVoid", 1),
        ("runSomeVoid", 1),
    ]


# ---------------------------------------------------------------------------
# U-AST-05 -- get_function_metadata(): constructor / modifier / @Test flags
# ---------------------------------------------------------------------------
def test_u_ast_05_get_function_metadata_flags(class_parser, java_tmp_main):
    classes = _focal_context_classes(class_parser, java_tmp_main)
    focal_class = next(c for c in classes if c["class_name"] == "FocalContext")
    methods = focal_class["methods"]

    assert [m["is_constructor"] for m in methods].count(True) == 2

    run_some_void_modifiers = [
        m["modifiers"] for m in methods if m["method_name"] == "runSomeVoid"
    ]
    assert len(run_some_void_modifiers) == 4
    assert run_some_void_modifiers.count("private") == 2

    assert all(m["is_testcase"] is False for m in methods)


# ---------------------------------------------------------------------------
# U-AST-06 -- parse_file(): syntactically invalid code yields no classes
# ---------------------------------------------------------------------------
def test_u_ast_06_parse_broken_file_returns_empty(class_parser, broken_java_file):
    assert class_parser.parse_file(str(broken_java_file)) == []


# ---------------------------------------------------------------------------
# U-AST-07 -- parse_file(): annotations, generics, duplicated imports
# ---------------------------------------------------------------------------
def test_u_ast_07_myclass_signature_and_imports(class_parser, myclass_java_path):
    classes = class_parser.parse_file(str(myclass_java_path))

    assert len(classes) == 1
    my_class = classes[0]
    assert my_class["class_name"] == "MyClass"
    assert (
        my_class["class_signature"]
        == "@AllConstructors\npublic class MyClass<T> extends Parent implements IAction, Clonable"
    )
    # ``import_list`` (ClassParser.py:70) does not deduplicate, so the repeated
    # ``import org.junit.Assert;`` is preserved: 4 static + 2 standard imports.
    assert len(my_class["imports"]) == 6
    assert my_class["imports"].count("import org.junit.Assert;") == 2


# ---------------------------------------------------------------------------
# U-AST-08 -- get_static_imports() / get_class_imports()
# ---------------------------------------------------------------------------
def test_u_ast_08_static_and_class_imports(class_parser, java_tmp_main):
    classes = _focal_context_classes(class_parser, java_tmp_main)
    imports = classes[0]["imports"]

    assert class_parser.get_static_imports(imports) == {
        "getSomeStrFrom03": "ExternalContext03",
        "getSomeStrFrom04": "ExternalContext04",
        "STATIC_INT_VAL": "StaticExternal01",
        "nonNull": "Objects",
    }
    assert class_parser.get_class_imports(imports) == [
        "ExternalContext01",
        "ExternalContext02",
        "StaticExternal01",
        "List",
        "Map",
    ]


# ---------------------------------------------------------------------------
# U-AST-09 -- regression: open() outside the try block propagates the error
# ---------------------------------------------------------------------------
@pytest.mark.regression
def test_u_ast_09_missing_file_raises_file_not_found(class_parser, tmp_path):
    missing = tmp_path / "does_not_exist" / "MissingClass.java"
    assert not missing.exists()

    with pytest.raises(FileNotFoundError):
        class_parser.parse_file(str(missing))
