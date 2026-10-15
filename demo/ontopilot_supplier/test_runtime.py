"""Requires the real OntoPilot dependencies; no network or LLM calls."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run  # configure upstream import path
from runtime import build_runtime


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "test.db"
        self.rt = build_runtime(self.db)
        self.params = {"supplierId": "SUP-001", "optionId": "OPT-MAT-001-FAST"}

    def execute(self, role, user, action, params):
        return self.rt.execute_action(user, role, action, params, confirmed=True)

    def test_links_and_functions_use_real_runtime(self):
        trace = self.rt.call_function("v", "viewer", "traceOrderRelations", {"orderId": "O1"})
        self.assertEqual(trace["customer"][0]["customerId"], "C1")
        self.assertEqual(trace["material"][0]["materialId"], "MAT-001")
        result = self.rt.call_function("v", "viewer", "assessSupplyOption", self.params)
        self.assertEqual(result["extraCost"], 20000)
        self.assertTrue(result["feasible"])

    def test_sqlite_workflow_persistence_and_audit(self):
        created = self.execute("buyer", "a", "submitSupplierChange", self.params)
        rid = created["result"]["requestId"]
        self.execute("approver", "b", "approveSupplierChange", {"requestId": rid})
        self.execute("buyer", "a", "executeSupplierChange", {"requestId": rid})
        reopened = build_runtime(self.db)
        self.assertEqual(reopened._store.get("Order", "O1")["supplierId"], "SUP-006")
        self.assertEqual(reopened._store.get("Order", "O3")["supplierId"], "SUP-001")
        self.assertEqual(reopened._store.get("Policy", "PROCUREMENT")["extraBudget"], 10000)
        self.assertGreaterEqual(len(reopened._audit.get_entries()), 3)
        orders = reopened.traverse("v", "viewer", "ChangeRequest", rid, "orders")
        self.assertEqual({o["orderId"] for o in orders}, {"O1", "O2"})

    def test_multi_order_failure_rolls_back(self):
        rid = self.execute("buyer", "a", "submitSupplierChange", self.params)["result"]["requestId"]
        self.execute("approver", "b", "approveSupplierChange", {"requestId": rid})
        store_type = type(self.rt._store)
        original_update = store_type.update

        def failing_update(store, kind, key, changes):
            if kind == "Order" and key == "O2":
                raise RuntimeError("injected failure")
            return original_update(store, kind, key, changes)

        with patch.object(store_type, "update", failing_update):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                self.execute("buyer", "a", "executeSupplierChange", {"requestId": rid})
        self.assertEqual(self.rt._store.get("Order", "O1")["supplierId"], "SUP-001")
        self.assertEqual(self.rt._store.get("Policy", "PROCUREMENT")["extraBudget"], 30000)
        self.assertEqual(self.rt._store.get("ChangeRequest", rid)["status"], "approved")

    def test_preserve_every_upstream_record_and_field(self):
        import yaml
        source = yaml.safe_load((run.UPSTREAM / "config/procurement_seed.yaml").read_text())
        for kind, rows in source.items():
            pk = self.rt._schema.get_object_type(kind).primary_key
            for row in rows:
                actual = self.rt._store.get(kind, row[pk])
                for key, value in row.items():
                    self.assertEqual(actual[key], value, (kind, row[pk], key))

    def test_supplier_with_multiple_materials_is_not_replaced_as_one_product(self):
        impact = self.rt.call_function("v", "viewer", "assessSupplierDelay", {"supplierId": "SUP-001"})
        self.assertEqual({m["materialId"] for m in impact["byMaterial"]}, {"MAT-001", "MAT-005"})
        result = self.rt.call_function("v", "viewer", "assessSupplyOption", self.params)
        self.assertEqual(result["orderIds"], ["O1", "O2"])
        self.assertEqual(result["requiredQuantity"], 1000)
        self.assertEqual(result["affectedSalesAmount"], 70000)
        wrong = self.rt.call_function("v", "viewer", "assessSupplyOption",
                                      {"supplierId": "SUP-002", "optionId": "OPT-MAT-001-FAST"})
        self.assertFalse(wrong["feasible"])

    def test_demonstration_stories_and_original_risk_function(self):
        overview = self.rt.call_function("v", "viewer", "getProcurementOverview", {})
        self.assertEqual(overview["counts"]["Order"], 48)
        self.assertEqual(overview["affectedOrderCount"], 8)
        self.assertEqual(overview["affectedSalesAmount"], 277000)
        self.assertEqual(len(self.rt._schema.object_type_names), 11)
        for sid, mid, expected in [("SUP-001", "MAT-001", True),
                                   ("SUP-002", "MAT-002", True),
                                   ("SUP-004", "MAT-004", False),
                                   ("SUP-001", "MAT-005", False)]:
            result = self.rt.call_function("v", "viewer", "compareSupplyOptions", {"supplierId": sid, "materialId": mid})
            self.assertEqual(any(o["feasible"] for o in result["options"]), expected)
        risk = self.rt.call_function("v", "viewer", "analyzeSupplyRisk", {"planId": "PLAN-DEMO-RISK"})
        self.assertEqual(risk["riskScore"], 85)
        self.assertEqual(risk["riskLevel"], "high")


if __name__ == "__main__":
    unittest.main()
