"""Hand-written metadata dictionaries consumed by ``build_format_corpus()``.

The dictionaries mirror the shape produced by
``DependencyParserUtils.parse_potential_focal_and_external_dependencies()``
(see ``tests/TEST_PLAN.md`` section C.2) and are intentionally independent of
the ``corpus/`` / ``dataset/`` folders, which are excluded by ``.rooignore``.

Every factory returns a brand new object (no shared mutable state between
tests).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

__all__ = [
    "PRIVATE_HELPER_METHOD",
    "PRIVATE_SECRET_FIELD",
    "PUBLIC_COUNTER_FIELD",
    "SAME_PACKAGE_EXTERNAL_DEPENDENCY",
    "metadata_focal_context",
    "metadata_focal_context_no_ext",
    "metadata_focal_context_no_priv",
    "metadata_invalid_sig",
    "metadata_myclass",
]

# ---------------------------------------------------------------------------
# Reusable building blocks (always deep-copied by the factories below).
# ---------------------------------------------------------------------------

PRIVATE_HELPER_METHOD: Dict[str, Any] = {
    "method_name": "helper",
    "parameters": "int val",
    "parameters_list": ["int val"],
    "modifiers": "private",
    "type_parameters": "",
    "return": "int",
    "body": "private int helper(int val) { return val; }",
    "signature": "helper(int val)",
    "full_signature": "private int helper(int val)",
    "full_signature_parameters": "private int helper(int val)",
    "class_method_signature": "helper(int)",
    "is_testcase": False,
    "is_constructor": False,
    "is_get_or_set": False,
}

PRIVATE_SECRET_FIELD: Dict[str, Any] = {
    "original_string": "private int secret;",
    "modifier": "private",
    "type": "int",
    "declarator": "secret",
    "var_name": "secret",
}

PUBLIC_COUNTER_FIELD: Dict[str, Any] = {
    "original_string": "public int counter;",
    "modifier": "public",
    "type": "int",
    "declarator": "counter",
    "var_name": "counter",
}

SAME_PACKAGE_EXTERNAL_DEPENDENCY: Dict[str, Any] = {
    "class_name": "SamePackageExternal01",
    "external_dependency": True,
    "superclass": "",
    "interfaces": "",
    "class_signature": "public class SamePackageExternal01",
    "has_constructor": False,
    "fields": [],
    "methods": [
        {
            "method_name": "getSomeStrFromSamePackExt01",
            "parameters": "",
            "parameters_list": [],
            "modifiers": "public",
            "type_parameters": "",
            "return": "String",
            "signature": "getSomeStrFromSamePackExt01()",
            "full_signature": "public String getSomeStrFromSamePackExt01()",
            "full_signature_parameters": "public String getSomeStrFromSamePackExt01()",
            "class_method_signature": "getSomeStrFromSamePackExt01()",
            "is_constructor": False,
        }
    ],
    "undefined_methods": [],
}


def _focal_class() -> Dict[str, Any]:
    """Canonical ``focal_class`` block for the FocalContext fixture."""
    return {
        "class_name": "FocalContext",
        "superclass": "extends Parent",
        "interfaces": "implements IAction, Clonable",
        "class_signature": "public class FocalContext extends Parent implements IAction, Clonable",
        "class_modifier": "public",
        "has_constructor": True,
        "fields": [
            deepcopy(PRIVATE_SECRET_FIELD),
            deepcopy(PUBLIC_COUNTER_FIELD),
        ],
        "methods": [
            {
                "method_name": "FocalContext",
                "full_signature": "public FocalContext()",
                "full_signature_parameters": "public FocalContext()",
                "modifiers": "public",
                "is_constructor": True,
            },
            {
                "method_name": "FocalContext",
                "full_signature": "public FocalContext(int val)",
                "full_signature_parameters": "public FocalContext(int val)",
                "modifiers": "public",
                "is_constructor": True,
            },
            {
                "method_name": "doSomething",
                "full_signature": "public String doSomething(int val)",
                "full_signature_parameters": "public String doSomething(int val)",
                "modifiers": "public",
                "is_constructor": False,
            },
            deepcopy(PRIVATE_HELPER_METHOD),
        ],
        "file": "FocalContext.java",
    }


def _focal_method(with_private_deps: bool = True) -> Dict[str, Any]:
    """Canonical ``focal_method`` block for the FocalContext fixture."""
    return {
        "method_name": "doSomething",
        "parameters": "int val",
        "parameters_list": ["int val"],
        "modifiers": "public",
        "body": "public String doSomething(int val) { return helper(val); }",
        "class_private_deps_used": {
            "methods": [deepcopy(PRIVATE_HELPER_METHOD)] if with_private_deps else [],
            "fields": [deepcopy(PRIVATE_SECRET_FIELD)] if with_private_deps else [],
        },
        "class_non_private_deps_used": {
            "methods": [],
            "fields": [deepcopy(PUBLIC_COUNTER_FIELD)],
        },
        "used_private_signatures_of_class": (
            ["private int helper(int val);", "private int secret;"] if with_private_deps else []
        ),
        "used_non_private_signatures_of_class": [
            "public FocalContext();",
            "public FocalContext(int val);",
            "public int counter;",
        ],
        "signatures_of_external_dependencies": {
            "public class SamePackageExternal01": ["public String getSomeStrFromSamePackExt01();"]
        },
        "external_dependencies": [deepcopy(SAME_PACKAGE_EXTERNAL_DEPENDENCY)],
    }


def metadata_focal_context() -> Dict[str, Any]:
    """Full dictionary matching the L1/L2/L3 expected literals of TEST_PLAN.md."""
    return {"focal_class": _focal_class(), "focal_method": _focal_method()}


def metadata_focal_context_no_ext() -> Dict[str, Any]:
    """Variant with no external dependencies (drives the ``<ECTX></ECTX>`` branch)."""
    metadata = metadata_focal_context()
    metadata["focal_method"]["external_dependencies"] = []
    metadata["focal_method"]["signatures_of_external_dependencies"] = {}
    return metadata


def metadata_focal_context_no_priv() -> Dict[str, Any]:
    """Variant with no private members used by the focal method."""
    metadata = metadata_focal_context()
    metadata["focal_method"]["class_private_deps_used"] = {"methods": [], "fields": []}
    metadata["focal_method"]["used_private_signatures_of_class"] = []
    return metadata


def metadata_invalid_sig() -> Dict[str, Any]:
    """Variant used when the class-signature validation is monkeypatched to fail."""
    metadata = metadata_focal_context()
    metadata["focal_class"]["class_signature"] = "public class FocalContext <T"
    return metadata


def metadata_myclass() -> Dict[str, Any]:
    """Metadata extracted conceptually from ``MyClass.java`` (annotated + generic)."""
    return {
        "focal_class": {
            "class_name": "MyClass",
            "superclass": "extends Parent",
            "interfaces": "implements IAction, Clonable",
            "class_signature": (
                "@AllConstructors\n"
                "public class MyClass<T> extends Parent implements IAction, Clonable"
            ),
            "class_modifier": "public",
            "has_constructor": True,
            "fields": [
                {
                    "original_string": "public static final String STATIC_VAR = \"Some static value\";",
                    "modifier": "public",
                    "type": "String",
                    "declarator": "STATIC_VAR",
                    "var_name": "STATIC_VAR",
                },
                {
                    "original_string": "private Long    [] values;",
                    "modifier": "private",
                    "type": "Long",
                    "declarator": "values",
                    "var_name": "values",
                },
            ],
            "methods": [
                {
                    "method_name": "MyClass",
                    "full_signature": "public <T> MyClass(String param)",
                    "full_signature_parameters": "public <T> MyClass(String param)",
                    "modifiers": "public",
                    "is_constructor": True,
                },
                {
                    "method_name": "testSerialization",
                    "full_signature": (
                        "public <T> void testSerialization("
                        "@Size Map.Entry<String, @Nullable String> entry, "
                        "MyClass myClass, Map<String, Object> map, "
                        "Integer someInteger, @NotNull int value[], Type... type)"
                    ),
                    "full_signature_parameters": (
                        "public <T> void testSerialization("
                        "@Size Map.Entry<String, @Nullable String> entry, "
                        "MyClass myClass, Map<String, Object> map, "
                        "Integer someInteger, @NotNull int value[], Type... type)"
                    ),
                    "modifiers": "public",
                    "is_constructor": False,
                },
            ],
            "file": "MyClass.java",
        },
        "focal_method": {
            "method_name": "testSerialization",
            "parameters": "java.lang.Object[]",
            "parameters_list": [],
            "modifiers": "public",
            "body": "public void testSerialization() { }",
            "class_private_deps_used": {"methods": [], "fields": []},
            "class_non_private_deps_used": {"methods": [], "fields": []},
            "signatures_of_external_dependencies": {},
            "external_dependencies": [],
        },
    }
