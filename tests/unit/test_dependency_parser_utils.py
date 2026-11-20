"""Unit tests for :mod:`dependency_parser_utils` (TEST_PLAN section B.3, U-DEP-01..U-DEP-06).

Targets
-------
* [`DependencyParserUtils.parse_potential_focal_and_external_dependencies()`](dependency_parser_utils.py:113)
* [`DependencyParserUtils.extract_info_from_dependency()`](dependency_parser_utils.py:322)
* [`DependencyParserUtils.get_methods_from_external_dependency()`](dependency_parser_utils.py:560)
* [`DependencyParserUtils.get_class_name()`](dependency_parser_utils.py:308)
* [`DependencyClassParser.parse_file()`](DependencyClassParser.py:27)

Environment
-----------
Verified against ``tree-sitter`` / ``tree-sitter-java`` **0.23.2** (the TEST_PLAN
was written for 0.21.0).  Every literal asserted below was observed on 0.23.2;
no literal from section B.3 had to be re-pinned.

Operational facts honoured here
-------------------------------
1. ``parse_potential_focal_and_external_dependencies()`` re-opens the path strings
   returned by
   [`get_path_imports()`](dependency_parser_utils.py:433) through
   [`extract_info_from_dependency()`](dependency_parser_utils.py:322) ->
   [`DependencyClassParser.parse_file()`](DependencyClassParser.py:39).
   Production relies on ``os.chdir(repo_path)``
   ([`find_map_tests_cases_from_repo.py:212`](find_map_tests_cases_from_repo.py:212)).
   These tests therefore both ``monkeypatch.chdir(java_tmp_tree)`` (mirroring
   production; ``monkeypatch`` restores the cwd) *and* feed the absolute POSIX
   paths of the ``all_focal_java_files`` fixture.  Nothing depends on the real
   repository cwd.
2. Fixture quirk kept as-is:
   [`SamePackageExternal01.java:1`](tests/fixtures/java/sample_java_repo/src/main/com/eljavatar/externals/SamePackageExternal01.java:1)
   declares ``package com.eljavatar.focals;`` while living under ``externals/``.
   Package matching is folder based
   ([`get_path_imports()`](dependency_parser_utils.py:465)), which is why the
   expected dependency set below is exactly
   ``{ExternalContext01, ExternalContext02, ExternalContext03,
   ExternalContext04, SamePackageExternal01, StaticExternal01}``.
3. Observed (and pinned) consequence of the aliasing at
   [`dependency_parser_utils.py:526`](dependency_parser_utils.py:526):
   ``paths_imports_and_package = paths_imports`` is an alias, not a copy, so the
   package paths are also added to ``paths_imports``.  A same-package/same-file
   class is consequently extracted twice (``path_import`` *and*
   ``path_in_package``), and
   [`dependency_parser_utils.py:407`](dependency_parser_utils.py:407) extends
   ``undefined_methods`` without de-duplicating.  This is what U-DEP-06 pins.
   Fields/methods are de-duplicated by signature at
   [`dependency_parser_utils.py:389`](dependency_parser_utils.py:389), so
   U-DEP-04/U-DEP-05 are unaffected.
4. ``FocalContext.java`` contains a package-private ``ExternalContext04`` next to
   the imported ``com.eljavatar.externals.ExternalContext04``, so ``doSomething``
   accumulates **two** dependency entries named ``ExternalContext04`` with
   different ``class_signature`` values (``public class ...`` vs
   ``class ...``); U-DEP-01/U-DEP-03 assertions are written as a set/mapping so
   that this duplication is harmless, and U-DEP-03 pins the entry count.
5. Not covered by U-DEP-01..06 (so not asserted here):
   [`DependencyClassParser.py:39`](DependencyClassParser.py:39) opens the file
   outside the ``try`` block, so a missing path raises ``FileNotFoundError``
   instead of returning ``None``.

All writes happen below ``tmp_path``; nothing touches the network or a
``.rooignore``d directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest

pytestmark = pytest.mark.unit

FOCAL_CONTEXT_RELATIVE_PATH = (
    Path("src") / "main" / "com" / "eljavatar" / "focals" / "FocalContext.java"
)

#: Observed dependency entries of ``FocalContext.doSomething`` on 0.23.2.
EXPECTED_DEPENDENCY_CLASS_NAMES = [
    "ExternalContext01",
    "ExternalContext02",
    "ExternalContext03",
    "ExternalContext04",
    "ExternalContext04",
    "SamePackageExternal01",
    "StaticExternal01",
]

#: Keys of every entry created at
#: [`dependency_parser_utils.py:414-424`](dependency_parser_utils.py:414).
EXPECTED_DEPENDENCY_KEYS = {
    "class_name",
    "external_dependency",
    "superclass",
    "interfaces",
    "class_signature",
    "has_constructor",
    "fields",
    "methods",
    "undefined_methods",
}


def _parse_focal_context_dependencies(
    class_parser,
    dependency_parser_utils,
    dependency_class_parser,
    java_tmp_tree: Path,
    all_focal_java_files: List[str],
) -> List[Dict[str, Any]]:
    """Run the full dependency flow over ``FocalContext.java`` in the tmp tree."""
    parsed_classes = class_parser.parse_file(str(java_tmp_tree / FOCAL_CONTEXT_RELATIVE_PATH))
    return dependency_parser_utils.parse_potential_focal_and_external_dependencies(
        dependency_class_parser, parsed_classes, all_focal_java_files
    )


def _do_something_method(parsed_classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return the ``FocalContext.doSomething`` method metadata (the only rich one)."""
    focal_class = next(c for c in parsed_classes if c["class_name"] == "FocalContext")
    return next(m for m in focal_class["methods"] if m["method_name"] == "doSomething")


def _dependency_by_name(method: Dict[str, Any], class_name: str) -> Dict[str, Any]:
    """Return the unique dependency entry whose ``class_name`` matches."""
    matches = [d for d in method["external_dependencies"] if d["class_name"] == class_name]
    assert len(matches) == 1, f"expected exactly one {class_name} dependency, got {len(matches)}"
    return matches[0]


# ---------------------------------------------------------------------------
# U-DEP-01 -- parse_potential...(): resolved external dependency class names
# ---------------------------------------------------------------------------
def test_u_dep_01_parse_potential_external_dependency_class_names(
    class_parser,
    dependency_parser_utils,
    dependency_class_parser,
    java_tmp_tree,
    all_focal_java_files,
    monkeypatch,
):
    monkeypatch.chdir(java_tmp_tree)

    parsed_classes = _parse_focal_context_dependencies(
        class_parser,
        dependency_parser_utils,
        dependency_class_parser,
        java_tmp_tree,
        all_focal_java_files,
    )
    dependencies = _do_something_method(parsed_classes)["external_dependencies"]

    # ExternalContext01: field + import + `ExternalContext01::methodReference`
    # SamePackageExternal01: field resolved through the package (folder based)
    # ExternalContext02/03: import + package (merged by class_signature)
    # ExternalContext04: static import + class declared in the same file
    # StaticExternal01: import + static import of STATIC_INT_VAL
    assert {d["class_name"] for d in dependencies} == {
        "ExternalContext01",
        "ExternalContext02",
        "ExternalContext03",
        "ExternalContext04",
        "SamePackageExternal01",
        "StaticExternal01",
    }
    # Deterministic order and count on 0.23.2 (ExternalContext04 appears twice:
    # imported class + package-private class in the same file).
    assert [d["class_name"] for d in dependencies] == EXPECTED_DEPENDENCY_CLASS_NAMES


# ---------------------------------------------------------------------------
# U-DEP-02 -- parse_potential...(): dotted nested types are discarded
# ---------------------------------------------------------------------------
def test_u_dep_02_parse_potential_skips_dotted_class_names(
    class_parser,
    dependency_parser_utils,
    dependency_class_parser,
    java_tmp_tree,
    all_focal_java_files,
    monkeypatch,
):
    monkeypatch.chdir(java_tmp_tree)

    parsed_classes = _parse_focal_context_dependencies(
        class_parser,
        dependency_parser_utils,
        dependency_class_parser,
        java_tmp_tree,
        all_focal_java_files,
    )
    dependencies = _do_something_method(parsed_classes)["external_dependencies"]

    # `Map.Entry` is filtered by get_class_name() + "." check
    # (dependency_parser_utils.py:220-223); Map.Entry never reaches the output.
    assert all("." not in d["class_name"] for d in dependencies)
    # get_class_name() only strips array/generic suffixes (dependency_parser_utils.py:308).
    assert dependency_parser_utils.get_class_name("Map.Entry") == "Map.Entry"
    assert dependency_parser_utils.get_class_name("List<ExternalContext01>") == "List"
    assert "Map" not in {d["class_name"] for d in dependencies}


# ---------------------------------------------------------------------------
# U-DEP-03 -- parse_potential...(): has_constructor per dependency
# ---------------------------------------------------------------------------
def test_u_dep_03_parse_potential_has_constructor_flags(
    class_parser,
    dependency_parser_utils,
    dependency_class_parser,
    java_tmp_tree,
    all_focal_java_files,
    monkeypatch,
):
    monkeypatch.chdir(java_tmp_tree)

    parsed_classes = _parse_focal_context_dependencies(
        class_parser,
        dependency_parser_utils,
        dependency_class_parser,
        java_tmp_tree,
        all_focal_java_files,
    )
    dependencies = _do_something_method(parsed_classes)["external_dependencies"]

    assert {d["class_name"]: d["has_constructor"] for d in dependencies} == {
        "ExternalContext01": True,
        "SamePackageExternal01": False,
        "ExternalContext02": False,
        "ExternalContext03": False,
        "ExternalContext04": False,
        "StaticExternal01": True,
    }
    # Seven entries: both `ExternalContext04` classes (imported + same file) are
    # present, see the module docstring (point 4).
    assert len(dependencies) == 7
    assert sum(d["class_name"] == "ExternalContext04" for d in dependencies) == 2


# ---------------------------------------------------------------------------
# U-DEP-04 -- extract_info_from_dependency(): same-package dependency payload
# ---------------------------------------------------------------------------
def test_u_dep_04_extract_info_same_package_dependency(
    class_parser,
    dependency_parser_utils,
    dependency_class_parser,
    java_tmp_tree,
    all_focal_java_files,
    monkeypatch,
):
    monkeypatch.chdir(java_tmp_tree)

    parsed_classes = _parse_focal_context_dependencies(
        class_parser,
        dependency_parser_utils,
        dependency_class_parser,
        java_tmp_tree,
        all_focal_java_files,
    )
    dependency = _dependency_by_name(_do_something_method(parsed_classes), "SamePackageExternal01")

    # Resolved from com/eljavatar/focals/SamePackageExternal01.java by package
    # matching (dependency_parser_utils.py:243), no import needed.
    assert dependency["class_signature"] == "public class SamePackageExternal01"
    assert dependency["external_dependency"] == "SamePackageExternal01"
    assert dependency["superclass"] == ""
    assert dependency["interfaces"] == ""
    assert dependency["fields"] == []
    assert [m["full_signature_parameters"] for m in dependency["methods"]] == [
        "public String getSomeStrFromSamePackExt01()"
    ]
    assert dependency["undefined_methods"] == []


# ---------------------------------------------------------------------------
# U-DEP-05 -- extract_info_from_dependency(): private members are excluded
# ---------------------------------------------------------------------------
def test_u_dep_05_extract_info_excludes_private_methods(
    class_parser,
    dependency_parser_utils,
    dependency_class_parser,
    java_tmp_tree,
    all_focal_java_files,
    monkeypatch,
):
    monkeypatch.chdir(java_tmp_tree)

    parsed_classes = _parse_focal_context_dependencies(
        class_parser,
        dependency_parser_utils,
        dependency_class_parser,
        java_tmp_tree,
        all_focal_java_files,
    )
    method = _do_something_method(parsed_classes)
    dependency = _dependency_by_name(method, "ExternalContext01")

    signatures = method["signatures_of_external_dependencies"][dependency["class_signature"]]

    assert "public String methodReference();" in signatures
    # Private method of the dependency is never extracted:
    # get_methods_from_external_dependency(..., allow_private=False)
    # (dependency_parser_utils.py:350, :560-572).
    assert "private String methodReference(Long val);" not in signatures
    assert all("private" not in signature for signature in signatures)
    # Pinned on 0.23.2 (empty parameter list keeps the parenthesis pair).
    assert [m["full_signature_parameters"] for m in dependency["methods"]] == [
        "public ExternalContext01()",
        "public String methodReference()",
        "public String methodReference(Integer)",
        "public String methodReference(Boolean)",
        "public Integer getSomeIntValue(boolean, boolean)",
        "public Integer getSomeIntValue(boolean, String)",
        "public Integer getSomeIntValue(String, boolean)",
    ]
    assert dependency["has_constructor"] is True
    # No matching declaration for the private `(String, String)` overload nor for
    # the `long` call, so they are reported as undefined (bucket at
    # dependency_parser_utils.py:594-599).
    assert dependency["undefined_methods"] == ["getSomeIntValue(String, long)"]


# ---------------------------------------------------------------------------
# U-DEP-06 -- extract_info_from_dependency(): undefined methods + entry schema
# ---------------------------------------------------------------------------
def test_u_dep_06_extract_info_undefined_methods_and_entry_keys(
    class_parser,
    dependency_parser_utils,
    dependency_class_parser,
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "proj"
    pkg = root / "pkg"
    pkg.mkdir(parents=True)
    # `Ext` deliberately does not declare `missingMethod()`.
    (pkg / "Ext.java").write_text(
        "package pkg;\n"
        "\n"
        "public class Ext {\n"
        "\n"
        "    public String existingMethod() {\n"
        '        return "";\n'
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    (pkg / "Focal2.java").write_text(
        "package pkg;\n"
        "\n"
        "public class Focal2 {\n"
        "\n"
        "    private Ext ext;\n"
        "\n"
        "    public String call() {\n"
        "        return ext.missingMethod();\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    java_files = sorted(path.as_posix() for path in pkg.rglob("*.java"))
    monkeypatch.chdir(root)

    parsed_classes = class_parser.parse_file(str(pkg / "Focal2.java"))
    parsed_classes = dependency_parser_utils.parse_potential_focal_and_external_dependencies(
        dependency_class_parser, parsed_classes, java_files
    )

    method = next(
        m for m in parsed_classes[0]["methods"] if m["method_name"] == "call"
    )
    dependency = _dependency_by_name(method, "Ext")

    # Bucket created at dependency_parser_utils.py:594-599 for a method that has
    # no declaration with matching name and arity.
    assert any(missing.startswith("missingMethod") for missing in dependency["undefined_methods"])
    # Observed on 0.23.2: the same-package class is extracted twice
    # (`path_import` and `path_in_package`, because of the alias at
    # dependency_parser_utils.py:526) and the undefined list is extended without
    # de-duplication (dependency_parser_utils.py:407).
    assert dependency["undefined_methods"] == ["missingMethod()", "missingMethod()"]
    assert dependency["class_signature"] == "public class Ext"
    assert dependency["external_dependency"] == "Ext"
    assert dependency["methods"] == []

    # Every emitted dependency has exactly the nine documented keys
    # (dependency_parser_utils.py:414-424).
    assert set(dependency.keys()) == EXPECTED_DEPENDENCY_KEYS
    for dep in method["external_dependencies"]:
        assert set(dep.keys()) == EXPECTED_DEPENDENCY_KEYS
