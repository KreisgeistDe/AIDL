from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import compiler_diagnostics  # noqa: E402


class DiagnosticActionabilityTest(unittest.TestCase):
    def test_legacy_json_without_actionability_metadata_is_unchanged(self) -> None:
        diagnostic = compiler_diagnostics.CompilerDiagnostic(
            code=compiler_diagnostics.CompilerDiagnosticCode.UNRESOLVED_IMPORT,
            phase="resolve",
            severity=compiler_diagnostics.CompilerDiagnosticSeverity.ERROR,
            message="unresolved import 'example.missing.Symbol'",
            source_path=Path("example.aidl"),
            location=compiler_diagnostics.Span(line=3, column=1, offset=17),
        )

        self.assertEqual(
            diagnostic.to_json(),
            {
                "code": "AIDL-R001",
                "phase": "resolve",
                "severity": "error",
                "message": "unresolved import 'example.missing.Symbol'",
                "location": {
                    "file": "example.aidl",
                    "line": 3,
                    "column": 1,
                    "offset": 17,
                },
            },
        )

    def test_missing_dist411_has_documented_metadata_and_insert_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "consumer StartReview {\n"
                "  start: workflow ReviewOrder(event.id)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                item for item in analysis.diagnostics if item.code == "AIDL-DIST411"
            )
            payload = diagnostic.to_json()

            self.assertEqual(payload["subject"], {"kind": "consumer", "name": "StartReview"})
            self.assertEqual(payload["expected"], "idempotency clause or proven pure body")
            self.assertEqual(
                payload["allowedFixes"],
                [
                    {
                        "kind": "insertClause",
                        "text": "idempotency: event.eventId retain 30d",
                    }
                ],
            )
            self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST411")

    def test_duplicate_dist411_has_metadata_without_insert_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "consumer.aidl"
            source.write_text(
                "module example.orders\n"
                "consumer ApplyOrder {\n"
                "  idempotency: event.eventId retain 30d\n"
                "  idempotency: event.eventId retain 7d\n"
                "  call: refreshOrder(event.id)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                item for item in analysis.diagnostics if item.code == "AIDL-DIST411"
            )
            payload = diagnostic.to_json()

            self.assertEqual(payload["subject"], {"kind": "consumer", "name": "ApplyOrder"})
            self.assertEqual(payload["expected"], "idempotency clause or proven pure body")
            self.assertNotIn("allowedFixes", payload)
            self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST411")

    def test_missing_dist404_has_clause_specific_metadata_without_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.orders\n"
                "mutation UpdateOrder() -> string {\n"
                "  auth: authenticated\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: Orders.update()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                item for item in analysis.diagnostics if item.code == "AIDL-DIST404"
            )
            payload = diagnostic.to_json()

            self.assertEqual(payload["subject"], {"kind": "mutation", "name": "UpdateOrder"})
            self.assertEqual(payload["expected"], "exactly one top-level allow clause")
            self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST404")
            self.assertNotIn("allowedFixes", payload)

    def test_duplicate_dist404_has_clause_specific_metadata_without_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.orders\n"
                "mutation UpdateOrder() -> string {\n"
                "  auth: authenticated\n"
                "  auth: service\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: Orders.update()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                item for item in analysis.diagnostics if item.code == "AIDL-DIST404"
            )
            payload = diagnostic.to_json()

            self.assertEqual(payload["subject"], {"kind": "mutation", "name": "UpdateOrder"})
            self.assertEqual(payload["expected"], "exactly one top-level auth clause")
            self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST404")
            self.assertNotIn("allowedFixes", payload)

    def test_all_missing_dist404_clauses_have_metadata_and_no_fixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.orders\n"
                "mutation EmptyMutation() -> string {\n"
                "  call: Orders.update()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostics = [
                item for item in analysis.diagnostics if item.code == "AIDL-DIST404"
            ]
            self.assertEqual(len(diagnostics), 4)
            self.assertEqual(
                [item.to_json()["expected"] for item in diagnostics],
                [
                    "exactly one top-level allow clause",
                    "exactly one top-level auth clause",
                    "exactly one top-level errors clause",
                    "exactly one top-level idempotency clause",
                ],
            )
            for diagnostic in diagnostics:
                payload = diagnostic.to_json()
                self.assertEqual(
                    payload["subject"],
                    {"kind": "mutation", "name": "EmptyMutation"},
                )
                self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST404")
                self.assertNotIn("allowedFixes", payload)

    def test_missing_dist405_has_metadata_without_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.orders\n"
                "mutation NoEffect() -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                item for item in analysis.diagnostics if item.code == "AIDL-DIST405"
            )
            payload = diagnostic.to_json()

            self.assertEqual(payload["code"], "AIDL-DIST405")
            self.assertEqual(payload["severity"], "error")
            self.assertEqual(
                payload["message"],
                "mutation 'example.orders.NoEffect' must have exactly one root effect; found 0",
            )
            self.assertEqual(payload["location"]["line"], 2)
            self.assertEqual(
                payload["subject"], {"kind": "mutation", "name": "NoEffect"}
            )
            self.assertEqual(payload["expected"], "exactly one top-level root effect")
            self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST405")
            self.assertNotIn("allowedFixes", payload)

    def test_multiple_dist405_has_metadata_without_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mutation.aidl"
            source.write_text(
                "module example.orders\n"
                "mutation TooManyEffects() -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [InvalidInput]\n"
                "  idempotency: none\n"
                "  call: Orders.update()\n"
                "  start: workflow AuditOrder()\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                item for item in analysis.diagnostics if item.code == "AIDL-DIST405"
            )
            payload = diagnostic.to_json()

            self.assertEqual(payload["code"], "AIDL-DIST405")
            self.assertEqual(payload["severity"], "error")
            self.assertEqual(
                payload["message"],
                "mutation 'example.orders.TooManyEffects' must have exactly one root effect; found 2",
            )
            self.assertEqual(payload["location"]["line"], 8)
            self.assertEqual(
                payload["subject"], {"kind": "mutation", "name": "TooManyEffects"}
            )
            self.assertEqual(payload["expected"], "exactly one top-level root effect")
            self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST405")
            self.assertNotIn("allowedFixes", payload)

    def test_actionability_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "consumer FirstConsumer {\n"
                "  call: doFirst(event.id)\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "consumer SecondConsumer {\n"
                "  start: workflow SecondWorkflow(event.id)\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])
            first_json = compiler_diagnostics.compiler_diagnostics_to_json(
                first_analysis.diagnostics
            )
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(
                second_analysis.diagnostics
            )

            self.assertEqual(first_json, second_json)
            payload = json.loads(first_json)
            self.assertEqual(
                [item["subject"]["name"] for item in payload],
                ["FirstConsumer", "SecondConsumer"],
            )
            self.assertEqual(
                [item["allowedFixes"][0]["kind"] for item in payload],
                ["insertClause", "insertClause"],
            )

    def test_dist404_actionability_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "mutation FirstMutation() -> string {\n"
                "  auth: authenticated\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "  call: First.update()\n"
                "}\n"
                "error Failure {\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "mutation SecondMutation() -> string {\n"
                "  auth: authenticated\n"
                "  auth: service\n"
                "  allow: true\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "  call: Second.update()\n"
                "}\n"
                "error Failure {\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])
            first_json = compiler_diagnostics.compiler_diagnostics_to_json(
                first_analysis.diagnostics
            )
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(
                second_analysis.diagnostics
            )

            self.assertEqual(first_json, second_json)
            payload = json.loads(first_json)
            self.assertEqual(
                [(item["subject"]["name"], item["expected"]) for item in payload],
                [
                    ("FirstMutation", "exactly one top-level allow clause"),
                    ("SecondMutation", "exactly one top-level auth clause"),
                ],
            )
            self.assertTrue(all("allowedFixes" not in item for item in payload))


    def test_dist405_actionability_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "mutation FirstMutation() -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "}\n"
                "error Failure {\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "mutation SecondMutation() -> string {\n"
                "  auth: authenticated\n"
                "  allow: true\n"
                "  errors: [Failure]\n"
                "  idempotency: none\n"
                "  call: Second.update()\n"
                "  start: saga SecondSaga()\n"
                "}\n"
                "error Failure {\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])
            first_json = compiler_diagnostics.compiler_diagnostics_to_json(
                first_analysis.diagnostics
            )
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(
                second_analysis.diagnostics
            )

            self.assertEqual(first_json, second_json)
            payload = json.loads(first_json)
            dist405 = [item for item in payload if item["code"] == "AIDL-DIST405"]
            self.assertEqual(
                [(item["subject"]["name"], item["expected"]) for item in dist405],
                [
                    ("FirstMutation", "exactly one top-level root effect"),
                    ("SecondMutation", "exactly one top-level root effect"),
                ],
            )
            self.assertTrue(all("allowedFixes" not in item for item in dist405))


    def test_dist403_all_effects_have_metadata_without_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "query.aidl"
            source.write_text(
                "module example.catalog\n"
                "query UnsafeQuery() -> string {\n"
                "  write: Store.update()\n"
                "  emit: Changed() to Events\n"
                "  call: Billing.charge()\n"
                "  start: workflow RebuildCatalog()\n"
                "  transaction on CatalogDb isolation serializable {\n"
                "    write: Store.update()\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostics = [
                item for item in analysis.diagnostics if item.code == "AIDL-DIST403"
            ]
            self.assertEqual(len(diagnostics), 5)
            self.assertEqual(
                [
                    item.message.split("found '", 1)[1].split("' effect", 1)[0]
                    for item in diagnostics
                ],
                ["write", "emit", "call", "start", "transaction"],
            )
            for diagnostic in diagnostics:
                payload = diagnostic.to_json()
                self.assertEqual(
                    payload["subject"], {"kind": "query", "name": "UnsafeQuery"}
                )
                self.assertEqual(payload["expected"], "side-effect-free query body")
                self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST403")
                self.assertNotIn("allowedFixes", payload)

    def test_dist403_actionability_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "query FirstQuery() -> string {\n"
                "  call: Search.refresh()\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "query SecondQuery() -> string {\n"
                "  transaction on CatalogDb isolation readCommitted {\n"
                "    write: CatalogDb.update()\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])
            first_json = compiler_diagnostics.compiler_diagnostics_to_json(
                first_analysis.diagnostics
            )
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(
                second_analysis.diagnostics
            )

            self.assertEqual(first_json, second_json)
            payload = json.loads(first_json)
            dist403 = [item for item in payload if item["code"] == "AIDL-DIST403"]
            self.assertEqual(
                [(item["subject"]["name"], item["expected"]) for item in dist403],
                [
                    ("FirstQuery", "side-effect-free query body"),
                    ("SecondQuery", "side-effect-free query body"),
                ],
            )
            self.assertTrue(all("allowedFixes" not in item for item in dist403))


    def test_dist413_page_and_list_have_metadata_without_fix_at_read_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "queries.aidl"
            source.write_text(
                "module example.queries\n"
                "query ListPets() -> Page<Pet> {\n"
                "  auth: private\n"
                "  read: Pet.where(active == true)\n"
                "}\n"
                "query RecentPets() -> [Pet] {\n"
                "  auth: private\n"
                "  read: Pet.where(active == true)\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostics = [
                item for item in analysis.diagnostics if item.code == "AIDL-DIST413"
            ]

            self.assertEqual(len(diagnostics), 2)
            self.assertEqual(
                [(item.location.line, item.location.column) for item in diagnostics],
                [(4, 3), (8, 3)],
            )
            self.assertEqual(
                [item.to_json()["subject"] for item in diagnostics],
                [
                    {"kind": "query", "name": "ListPets"},
                    {"kind": "query", "name": "RecentPets"},
                ],
            )
            for diagnostic in diagnostics:
                payload = diagnostic.to_json()
                self.assertEqual(payload["expected"], "explicit page or limit bound in read path")
                self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST413")
                self.assertNotIn("allowedFixes", payload)

    def test_dist413_missing_read_anchors_query_and_has_no_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "queries.aidl"
            source.write_text(
                "module example.queries\n"
                "query ListPets() -> [Pet] {\n"
                "  auth: private\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                item for item in analysis.diagnostics if item.code == "AIDL-DIST413"
            )
            payload = diagnostic.to_json()

            self.assertEqual((diagnostic.location.line, diagnostic.location.column), (2, 1))
            self.assertEqual(payload["subject"], {"kind": "query", "name": "ListPets"})
            self.assertEqual(payload["expected"], "explicit page or limit bound in read path")
            self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST413")
            self.assertNotIn("allowedFixes", payload)

    def test_dist413_actionability_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "query FirstQuery() -> Page<Item> {\n"
                "  auth: private\n"
                "  read: Item.all()\n"
                "}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "query SecondQuery() -> [Item] {\n"
                "  auth: private\n"
                "}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])
            first_json = compiler_diagnostics.compiler_diagnostics_to_json(
                item for item in first_analysis.diagnostics if item.code == "AIDL-DIST413"
            )
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(
                item for item in second_analysis.diagnostics if item.code == "AIDL-DIST413"
            )

            self.assertEqual(first_json, second_json)
            payload = json.loads(first_json)
            self.assertEqual(
                [(item["subject"]["name"], item["expected"]) for item in payload],
                [
                    ("FirstQuery", "explicit page or limit bound in read path"),
                    ("SecondQuery", "explicit page or limit bound in read path"),
                ],
            )
            self.assertTrue(all("allowedFixes" not in item for item in payload))


    def test_missing_dist400_has_metadata_without_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "entity.aidl"
            source.write_text(
                "module example.domain\n"
                "entity Pet {\n}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                item for item in analysis.diagnostics if item.code == "AIDL-DIST400"
            )
            payload = diagnostic.to_json()

            self.assertEqual(payload["code"], "AIDL-DIST400")
            self.assertEqual(payload["severity"], "error")
            self.assertEqual(
                payload["message"],
                "persisted entity 'example.domain.Pet' must have exactly one owner service; found none",
            )
            self.assertEqual(
                (payload["location"]["line"], payload["location"]["column"]),
                (2, 1),
            )
            self.assertEqual(payload["subject"], {"kind": "entity", "name": "Pet"})
            self.assertEqual(payload["expected"], "exactly one owner service")
            self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST400")
            self.assertNotIn("allowedFixes", payload)

    def test_multiple_dist400_has_metadata_without_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entity = root / "a-domain.aidl"
            first_service = root / "b-first.aidl"
            second_service = root / "c-second.aidl"
            entity.write_text(
                "module example.domain\n"
                "export entity Pet {\n}\n",
                encoding="utf-8",
            )
            first_service.write_text(
                "module example.first\n"
                "import example.domain.Pet\n"
                "service FirstService {\n"
                "  owns [Pet]\n"
                "}\n",
                encoding="utf-8",
            )
            second_service.write_text(
                "module example.second\n"
                "import example.domain.*\n"
                "service SecondService {\n"
                "  owns [Pet]\n"
                "}\n",
                encoding="utf-8",
            )

            analysis = compiler_diagnostics.load_compiler_analysis([root])
            diagnostic = next(
                item for item in analysis.diagnostics if item.code == "AIDL-DIST400"
            )
            payload = diagnostic.to_json()

            self.assertEqual(payload["code"], "AIDL-DIST400")
            self.assertEqual(payload["severity"], "error")
            self.assertEqual(
                payload["message"],
                "persisted entity 'example.domain.Pet' must have exactly one owner service; found 2: example.first.FirstService, example.second.SecondService",
            )
            self.assertEqual(
                (payload["location"]["line"], payload["location"]["column"]),
                (2, 8),
            )
            self.assertEqual(payload["subject"], {"kind": "entity", "name": "Pet"})
            self.assertEqual(payload["expected"], "exactly one owner service")
            self.assertEqual(payload["docs"], "aidl://diagnostics/AIDL-DIST400")
            self.assertNotIn("allowedFixes", payload)

    def test_dist400_actionability_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "a-first.aidl"
            second = root / "b-second.aidl"
            first.write_text(
                "module example.first\n"
                "entity FirstEntity {\n}\n",
                encoding="utf-8",
            )
            second.write_text(
                "module example.second\n"
                "entity SecondEntity {\n}\n",
                encoding="utf-8",
            )

            first_analysis = compiler_diagnostics.load_compiler_analysis([root])
            second_analysis = compiler_diagnostics.load_compiler_analysis([second, first])
            first_json = compiler_diagnostics.compiler_diagnostics_to_json(
                item for item in first_analysis.diagnostics if item.code == "AIDL-DIST400"
            )
            second_json = compiler_diagnostics.compiler_diagnostics_to_json(
                item for item in second_analysis.diagnostics if item.code == "AIDL-DIST400"
            )

            self.assertEqual(first_json, second_json)
            payload = json.loads(first_json)
            self.assertEqual(
                [(item["subject"]["name"], item["expected"]) for item in payload],
                [
                    ("FirstEntity", "exactly one owner service"),
                    ("SecondEntity", "exactly one owner service"),
                ],
            )
            self.assertTrue(
                all(item["docs"] == "aidl://diagnostics/AIDL-DIST400" for item in payload)
            )
            self.assertTrue(all("allowedFixes" not in item for item in payload))


if __name__ == "__main__":
    unittest.main()