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
        self.params = {"supplierId": "S1", "optionId": "OPT-S2-P1"}

    def execute(self, role, user, action, params):
        return self.rt.execute_action(user, role, action, params, confirmed=True)

    def test_links_and_functions_use_real_runtime(self):
        trace = self.rt.call_function("v", "viewer", "traceOrderRelations", {"orderId": "O1"})
        self.assertEqual(trace["customer"][0]["customerId"], "C1")
        self.assertEqual(trace["product"][0]["productId"], "P1")
        result = self.rt.call_function("v", "viewer", "assessSupplyOption", self.params)
        self.assertEqual(result["extraCost"], 2000)
        self.assertTrue(result["feasible"])

    def test_sqlite_workflow_persistence_and_audit(self):
        created = self.execute("buyer", "a", "submitSupplierChange", self.params)
        rid = created["result"]["requestId"]
        self.execute("approver", "b", "approveSupplierChange", {"requestId": rid})
        self.execute("buyer", "a", "executeSupplierChange", {"requestId": rid})
        reopened = build_runtime(self.db)
        self.assertEqual(reopened._store.get("Order", "O1")["supplierId"], "S2")
        self.assertEqual(reopened._store.get("Order", "O3")["supplierId"], "S1")
        self.assertEqual(reopened._store.get("Policy", "PROCUREMENT")["extraBudget"], 1000)
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
        self.assertEqual(self.rt._store.get("Order", "O1")["supplierId"], "S1")
        self.assertEqual(self.rt._store.get("Policy", "PROCUREMENT")["extraBudget"], 3000)
        self.assertEqual(self.rt._store.get("ChangeRequest", rid)["status"], "approved")


if __name__ == "__main__":
    unittest.main()
