"""Scope: the vocabulary for what an instruction may change."""

from __future__ import annotations

import unittest

from verifier.log import Rename, Scope, ScopeError


class ScopeTests(unittest.TestCase):
    def test_an_empty_scope_allows_no_boundary_change(self):
        self.assertEqual(Scope().renames, ())
        self.assertIn("no boundary change allowed", Scope().describe())

    def test_a_rename_describes_both_names(self):
        rename = Rename("app.maths.double", "app.maths.twice")
        self.assertEqual(rename.describe(), "rename app.maths.double to app.maths.twice")

    def test_scope_survives_json(self):
        scope = Scope((Rename("app.maths.double", "app.numbers.double"),))
        self.assertEqual(Scope.from_json(scope.to_json()), scope)

    def test_names_must_be_qualified(self):
        for bad in ("double", "app.maths.", "app..double", "app.maths.dou ble", ""):
            with self.subTest(name=bad), self.assertRaises(ScopeError):
                Rename(bad, "app.maths.twice")

    def test_a_rename_must_change_the_name(self):
        with self.assertRaises(ScopeError):
            Rename("app.maths.double", "app.maths.double")

    def test_an_unknown_kind_of_boundary_change_is_rejected(self):
        with self.assertRaisesRegex(ScopeError, "unsupported boundary change"):
            Scope.from_json({"boundary_changes": [{"op": "delete", "from": "app.maths.double"}]})
