"""Topology extraction: public symbols, signatures, imports, fingerprints."""

from __future__ import annotations

from tests.support import ScratchTestCase, write_files
from verifier.snapshot import Topology, extract_topology


class ExtractTests(ScratchTestCase):
    def extract(self, files) -> Topology:
        files = {"pkg/__init__.py": "", **files}
        return extract_topology(write_files(self.scratch, files), ("pkg",))

    def test_public_functions_are_recorded_with_their_signature(self):
        topology = self.extract({"pkg/a.py": "def area(width, height=1, *, unit='m'): return 0"})
        symbol = topology.symbols["pkg.a.area"]
        self.assertEqual(symbol.kind, "function")
        self.assertEqual(symbol.signature, "(width, height=1, *, unit='m')")

    def test_private_names_are_not_part_of_the_interface(self):
        topology = self.extract({"pkg/a.py": "_RATE = 2\ndef _helper(): pass\ndef api(): pass"})
        self.assertEqual(set(topology.symbols), {"pkg.a.api"})

    def test_classes_expose_their_public_methods(self):
        source = """
            class Cart:
                def __init__(self, owner): self.owner = owner
                def add(self, sku, quantity=1): pass
                def _recount(self): pass
        """
        symbol = self.extract({"pkg/a.py": source}).symbols["pkg.a.Cart"]
        self.assertEqual(symbol.kind, "class")
        self.assertEqual(symbol.signature, "__init__(self, owner); add(self, sku, quantity=1)")

    def test_module_level_constants_are_public_symbols(self):
        topology = self.extract({"pkg/a.py": "LIMIT = 10\nRATE: float = 0.5"})
        self.assertEqual({s.kind for s in topology.symbols.values()}, {"constant"})
        self.assertEqual(set(topology.symbols), {"pkg.a.LIMIT", "pkg.a.RATE"})

    def test_every_module_is_listed_even_without_imports(self):
        files = {"pkg/a.py": "X = 1", "pkg/sub/__init__.py": "", "pkg/sub/b.py": ""}
        topology = self.extract(files)
        self.assertEqual(topology.modules, ("pkg", "pkg.a", "pkg.sub", "pkg.sub.b"))

    def test_internal_imports_are_recorded_and_external_ones_ignored(self):
        source = """
            import os
            import pkg.b
            from decimal import Decimal
            from pkg.b import helper

            def lazy():
                from pkg.c import late
        """
        topology = self.extract({"pkg/a.py": source, "pkg/b.py": "", "pkg/c.py": ""})
        self.assertEqual(topology.imports["pkg.a"], ("pkg.b", "pkg.b.helper", "pkg.c.late"))

    def test_relative_imports_are_resolved(self):
        files = {
            "pkg/sub/__init__.py": "from . import b\nfrom .b import one",
            "pkg/sub/b.py": "from ..a import two\nfrom .. import a",
            "pkg/a.py": "",
        }
        topology = self.extract(files)
        self.assertEqual(topology.imports["pkg.sub"], ("pkg.sub.b", "pkg.sub.b.one"))
        self.assertEqual(topology.imports["pkg.sub.b"], ("pkg.a", "pkg.a.two"))

    def test_a_module_that_cannot_be_parsed_exposes_nothing(self):
        topology = self.extract({"pkg/a.py": "def broken(:"})
        self.assertEqual(dict(topology.symbols), {})
        self.assertIn("pkg.a", topology.modules)

    def test_topology_survives_json(self):
        topology = self.extract({"pkg/a.py": "from pkg.b import x\ndef f(): pass", "pkg/b.py": ""})
        self.assertEqual(Topology.from_json(topology.to_json()), topology)


class FingerprintTests(ScratchTestCase):
    def fingerprint(self, source: str, name: str) -> str:
        files = {"pkg/__init__.py": "", "pkg/a.py": source}
        topology = extract_topology(write_files(self.scratch, files), ("pkg",))
        return topology.symbols[f"pkg.a.{name}"].fingerprint

    def test_a_pure_rename_keeps_the_fingerprint(self):
        before = self.fingerprint("def old(x):\n    return x + 1\n", "old")
        after = self.fingerprint("def new(x):\n    return x + 1\n", "new")
        self.assertEqual(before, after)

    def test_comments_layout_and_docstrings_do_not_matter(self):
        plain = self.fingerprint("def f(x):\n    return x + 1\n", "f")
        dressed = self.fingerprint(
            'def f(x):\n    """Add one."""\n    # explain\n    return (x +\n        1)\n', "f"
        )
        self.assertEqual(plain, dressed)

    def test_a_changed_body_changes_the_fingerprint(self):
        before = self.fingerprint("def f(x):\n    return x >= 10\n", "f")
        after = self.fingerprint("def f(x):\n    return x > 10\n", "f")
        self.assertNotEqual(before, after)
