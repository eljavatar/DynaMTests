"""Builders for synthetic mining JSON files (stage 1 output shape).

A mining JSON file is one *mapped test case*: it contains the keys
``test_class``, ``test_case``, ``focal_class``, ``focal_method`` and
``repository`` (see ``find_map_tests_cases_from_repo.py:679`` — ``export_mtc``).
Only the fields actually consumed by later stages are populated:

* ``clean_duplicates_and_build_dataset.py`` reads ``test_case.body``,
  ``focal_method.body`` and ``repository.url``.
* ``build_corpus.py`` reads ``test_class.imports``, ``test_case.body`` /
  ``modifiers``, and several blocks of ``focal_class`` / ``focal_method``.

All bodies are syntactically valid Java so that the syntactic filters of
``build_corpus`` can accept them.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from fixtures.metadata_samples import SAME_PACKAGE_EXTERNAL_DEPENDENCY

__all__ = [
    "DEFAULT_BODY_FOCAL",
    "DEFAULT_BODY_TEST",
    "make_mtc_json",
    "make_corpus_record",
    "CORPUS_RECORD_KEYS",
]

DEFAULT_BODY_FOCAL = 'public String doSomething(int val) { return "value"; }'
DEFAULT_BODY_TEST = (
    'public void testDoSomething() { '
    'Assert.assertEquals("value", new SampleFocal().doSomething(1)); }'
)

CORPUS_RECORD_KEYS = (
    "target",
    "src_fm_fc_ms_ff",
    "src_fm_fc_dctx",
    "src_fm_fc_dctx_priv",
    "imports_focal_class",
    "imports_test_class",
)


def _focal_class(focal_class_name: str, with_constructor: bool = True) -> Dict[str, Any]:
    methods = []
    if with_constructor:
        methods.append(
            {
                "method_name": focal_class_name,
                "full_signature": f"public {focal_class_name}()",
                "full_signature_parameters": f"public {focal_class_name}()",
                "modifiers": "public",
                "is_constructor": True,
            }
        )
    methods.append(
        {
            "method_name": "doSomething",
            "full_signature": "public String doSomething(int val)",
            "full_signature_parameters": "public String doSomething(int val)",
            "modifiers": "public",
            "is_constructor": False,
        }
    )
    return {
        "class_name": focal_class_name,
        "superclass": "",
        "interfaces": "",
        "class_signature": f"public class {focal_class_name}",
        "class_modifier": "public",
        "has_constructor": with_constructor,
        "fields": [
            {
                "original_string": "public int counter;",
                "modifier": "public",
                "type": "int",
                "declarator": "counter",
                "var_name": "counter",
            }
        ],
        "methods": methods,
        "imports": ["import org.junit.Assert;", "import java.util.List;"],
        "package": "package com.example.sample;",
        "file": f"src/main/java/com/example/sample/{focal_class_name}.java",
    }


def _focal_method(body_focal: str, with_external_dependency: bool) -> Dict[str, Any]:
    return {
        "method_name": "doSomething",
        "parameters": "int val",
        "parameters_list": ["int val"],
        "modifiers": "public",
        "body": body_focal,
        "class_private_deps_used": {"methods": [], "fields": []},
        "class_non_private_deps_used": {"methods": [], "fields": []},
        "used_private_signatures_of_class": [],
        "used_non_private_signatures_of_class": ["public int counter;"],
        "signatures_of_external_dependencies": (
            {"public class SamePackageExternal01": ["public String getSomeStrFromSamePackExt01();"]}
            if with_external_dependency
            else {}
        ),
        "external_dependencies": (
            [deepcopy(SAME_PACKAGE_EXTERNAL_DEPENDENCY)] if with_external_dependency else []
        ),
    }


def make_mtc_json(
    body_focal: str = DEFAULT_BODY_FOCAL,
    body_test: str = DEFAULT_BODY_TEST,
    url: str = "https://example.invalid/sample-repo",
    repo_id: str = "123",
    focal_class_name: str = "SampleFocal",
    with_external_dependency: bool = False,
    test_modifiers: str = "@Test",
    test_case_name: str = "testDoSomething",
) -> Dict[str, Any]:
    """Return a mining JSON-ready dict (one mapped test case)."""
    return {
        "test_class": {
            "class_name": f"{focal_class_name}Test",
            "superclass": "",
            "interfaces": "",
            "class_signature": f"public class {focal_class_name}Test",
            "class_modifier": "public",
            "has_constructor": False,
            "fields": [],
            "imports": [
                "import org.junit.Test;",
                "import org.junit.Assert;",
                f"import com.example.sample.{focal_class_name};",
            ],
            "package": "package com.example.sample;",
            "file": (
                f"src/test/java/com/example/sample/{focal_class_name}Test.java"
            ),
        },
        "test_case": {
            "method_name": test_case_name,
            "parameters": "",
            "parameters_list": [],
            "modifiers": test_modifiers,
            "body": body_test,
            "signature": f"{test_case_name}()",
            "full_signature": f"public void {test_case_name}()",
            "is_testcase": True,
            "is_constructor": False,
        },
        "focal_class": _focal_class(focal_class_name),
        "focal_method": _focal_method(body_focal, with_external_dependency),
        "repository": {"repo_id": repo_id, "url": url},
    }


def make_corpus_record(index: int = 0) -> Dict[str, str]:
    """Return one corpus JSON record with the six canonical keys of stage 3."""
    return {
        "target": f'public void testCase{index}() {{ Assert.assertEquals({index}, {index}); }}',
        "src_fm_fc_ms_ff": (
            f"public class SampleFocal {{ public String doSomething(int val) "
            f'{{ return "value"; }} public int counter; }}'
        ),
        "src_fm_fc_dctx": (
            f"<FCTX>public class SampleFocal {{ public String doSomething(int val) "
            f'{{ return "value"; }} public int counter; }}</FCTX> <ECTX></ECTX>'
        ),
        "src_fm_fc_dctx_priv": (
            f"<FCTX>public class SampleFocal {{ public String doSomething(int val) "
            f'{{ return "value"; }} public int counter; }} '
            f"<PRIVATE_FCTX></PRIVATE_FCTX></FCTX> <ECTX></ECTX>"
        ),
        "imports_focal_class": "import org.junit.Assert;|import java.util.List;",
        "imports_test_class": "import org.junit.Test;|import org.junit.Assert;",
    }
