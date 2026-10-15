"""Tests execute the actual domain rules without network or third-party packages."""
from __future__ import annotations

import copy
import unittest

from domain import SupplierService


class MemoryStore:
    def __init__(self):
        self._in_memory = {
            "Supplier": {
                "S1": {"supplierId": "S1", "delayDays": 7, "status": "active"},
                "S2": {"supplierId": "S2", "delayDays": 0, "status": "active"},
            },
            "Order": {
                "O1": {"orderId": "O1", "supplierId": "S1", "productId": "P1", "quantity": 60, "salesAmount": 60000, "bufferDays": 3},
                "O2": {"orderId": "O2", "supplierId": "S1", "productId": "P1", "quantity": 40, "salesAmount": 40000, "bufferDays": 5},
                "O3": {"orderId": "O3", "supplierId": "S1", "productId": "P1", "quantity": 20, "salesAmount": 20000, "bufferDays": 10},
            },
            "SupplyOption": {"OPT": {"optionId": "OPT", "supplierId": "S2", "productId": "P1", "availableQuantity": 100, "extraUnitCost": 20, "onTime": True}},
            "Policy": {"PROCUREMENT": {"policyId": "PROCUREMENT", "extraBudget": 3000}},
            "ChangeRequest": {},
        }

    def get(self, kind, key):
        return copy.deepcopy(self._in_memory.get(kind, {}).get(key))

    def query(self, kind, filters, properties):
        return [copy.deepcopy(o) for o in self._in_memory.get(kind, {}).values()
                if all(o.get(k) == v for k, v in filters.items())]

    def update(self, kind, key, changes):
        self._in_memory[kind][key].update(changes)
        return self.get(kind, key)

    def create(self, kind, data):
        self._in_memory[kind][data["requestId"]] = copy.deepcopy(data)
        return copy.deepcopy(data)


class SupplierRulesTest(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.service = SupplierService(self.store)
        self.params = {"supplierId": "S1", "optionId": "OPT"}

    def submit(self):
        return self.service.execute("buyer", "buyer-a", "submitSupplierChange", self.params, True)["result"]["requestId"]

    def approve(self, request_id):
        return self.service.execute("approver", "approver-b", "approveSupplierChange", {"requestId": request_id}, True)

    def test_affected_orders_and_sales_not_loss(self):
        result = self.service.assess_delay(self.params)
        self.assertEqual(result["orderIds"], ["O1", "O2"])
        self.assertEqual(result["requiredQuantity"], 100)
        self.assertEqual(result["affectedSalesAmount"], 100000)

    def test_option_cost(self):
        result = self.service.assess_option(self.params)
        self.assertTrue(result["feasible"])
        self.assertEqual(result["extraCost"], 2000)

    def test_low_budget_and_cannot_expand_policy_budget(self):
        self.assertFalse(self.service.assess_option({**self.params, "budget": 1000})["feasible"])
        self.store.update("Policy", "PROCUREMENT", {"extraBudget": 1000})
        self.assertFalse(self.service.assess_option({**self.params, "budget": 999999})["feasible"])
        with self.assertRaises(KeyError):
            self.submit()

    def test_stock_product_time_and_supplier_guards(self):
        for change in [{"availableQuantity": 99}, {"productId": "P2"}, {"onTime": False}]:
            with self.subTest(change=change):
                original = self.store.get("SupplyOption", "OPT")
                self.store.update("SupplyOption", "OPT", change)
                self.assertFalse(self.service.assess_option(self.params)["feasible"])
                self.store.update("SupplyOption", "OPT", original)
        self.store.update("Supplier", "S2", {"status": "inactive"})
        self.assertFalse(self.service.assess_option(self.params)["feasible"])

    def test_confirmation_and_roles(self):
        with self.assertRaises(PermissionError):
            self.service.execute("buyer", "a", "submitSupplierChange", self.params, False)
        with self.assertRaises(PermissionError):
            self.service.execute("viewer", "a", "submitSupplierChange", self.params, True)
        request_id = self.submit()
        with self.assertRaises(PermissionError):
            self.service.execute("buyer", "a", "approveSupplierChange", {"requestId": request_id}, True)

    def test_no_self_approval(self):
        request_id = self.submit()
        with self.assertRaises(PermissionError):
            self.service.execute("approver", "buyer-a", "approveSupplierChange", {"requestId": request_id}, True)

    def test_cannot_execute_pending_request(self):
        request_id = self.submit()
        with self.assertRaises(KeyError):
            self.service.execute("buyer", "buyer-a", "executeSupplierChange", {"requestId": request_id}, True)

    def test_stale_approval_is_rejected(self):
        request_id = self.submit()
        self.approve(request_id)
        self.store.update("SupplyOption", "OPT", {"availableQuantity": 101})
        with self.assertRaisesRegex(KeyError, "变化"):
            self.service.execute("buyer", "buyer-a", "executeSupplierChange", {"requestId": request_id}, True)
        self.assertEqual(self.store.get("Order", "O1")["supplierId"], "S1")

    def test_execute_updates_only_affected_orders_and_consumes_resources(self):
        request_id = self.submit()
        self.approve(request_id)
        result = self.service.execute("buyer", "buyer-a", "executeSupplierChange", {"requestId": request_id}, True)
        self.assertEqual(result["result"]["status"], "executed")
        for oid in ["O1", "O2"]:
            self.assertEqual(self.store.get("Order", oid)["supplierId"], "S2")
        self.assertEqual(self.store.get("Order", "O3")["supplierId"], "S1")
        self.assertEqual(self.store.get("SupplyOption", "OPT")["availableQuantity"], 0)
        self.assertEqual(self.store.get("Policy", "PROCUREMENT")["extraBudget"], 1000)
        with self.assertRaises(KeyError):
            self.service.execute("buyer", "buyer-a", "executeSupplierChange", {"requestId": request_id}, True)


if __name__ == "__main__":
    unittest.main()
