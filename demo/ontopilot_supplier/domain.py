"""供应商教学场景的确定性规则；模型不负责计算或审批校验。"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal


class SupplierService:
    def __init__(self, store):
        self.store = store

    def require(self, kind, key):
        obj = self.store.get(kind, key)
        if obj is None:
            raise KeyError(f"{kind}:{key} 不存在")
        return obj

    def assess_delay(self, params):
        supplier = self.require("Supplier", params["supplierId"])
        orders = self.store.query("Order", {"supplierId": supplier["supplierId"]}, None)
        orders = [o for o in orders if o.get("status", "open") == "open"
                  and (not params.get("materialId") or o["materialId"] == params["materialId"])]
        affected = [o for o in orders if supplier["delayDays"] > o["bufferDays"]]
        by_material = {}
        for order in affected:
            group = by_material.setdefault(order["materialId"], {"materialId": order["materialId"], "quantity": 0, "salesAmount": 0})
            group["quantity"] += order["quantity"]
            group["salesAmount"] += order["salesAmount"]
        return {
            "supplierId": supplier["supplierId"], "delayDays": supplier["delayDays"],
            "orderIds": [o["orderId"] for o in affected],
            "affectedSalesAmount": float(sum(Decimal(str(o["salesAmount"])) for o in affected)),
            "requiredQuantity": sum(o["quantity"] for o in affected),
            "orders": affected, "currency": "CNY",
            "byMaterial": list(by_material.values()),
            "note": "受影响销售额不是已发生损失；不计库存和排程调整。",
        }

    def assess_option(self, params):
        option = self.require("SupplyOption", params["optionId"])
        if params.get("materialId") and params["materialId"] != option["materialId"]:
            raise KeyError("指定物料与供货选项不匹配")
        impact = self.assess_delay({**params, "materialId": option["materialId"]})
        supplier = self.require("Supplier", option["supplierId"])
        policy = self.require("Policy", "PROCUREMENT")
        cost = Decimal(str(option["extraUnitCost"])) * impact["requiredQuantity"]
        budget = Decimal(str(policy["extraBudget"]))
        # A what-if budget can tighten the policy, never expand authorization.
        if "budget" in params:
            candidate = Decimal(str(params["budget"]))
            if not candidate.is_finite() or candidate < 0:
                raise KeyError("budget 必须为非负有限数值")
            budget = min(budget, candidate)
        reasons = []
        if option.get("sourceSupplierId", params["supplierId"]) != params["supplierId"]:
            reasons.append("增量报价对应的原供应商不匹配")
        if not impact["orders"]:
            reasons.append("没有需要替换供应商的订单")
        if option["supplierId"] == params["supplierId"] or supplier["status"] != "active":
            reasons.append("备选供应商不可用")
        if not option["onTime"]:
            reasons.append("无法及时交付")
        if option["availableQuantity"] < impact["requiredQuantity"]:
            reasons.append("可用数量不足")
        if cost > budget:
            reasons.append("超出额外采购预算")
        result = {
            **impact, "optionId": option["optionId"],
            "replacementSupplierId": option["supplierId"],
            "materialId": option["materialId"],
            "extraCost": float(cost), "extraUnitCost": option["extraUnitCost"],
            "budget": float(budget), "availableQuantity": option["availableQuantity"],
            "feasible": not reasons, "reasons": reasons,
        }
        snapshot = {"orders": impact["orders"], "option": option, "supplier": supplier,
                    "originalSupplier": self.require("Supplier", params["supplierId"]),
                    "policy": policy}
        result["snapshot"] = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        return result

    def request_details(self, params):
        return self.require("ChangeRequest", params["requestId"])

    def trace_order(self, params):
        order = self.require("Order", params["orderId"])
        purchase_orders = self.store.traverse("Order", order["orderId"], "originalPurchaseOrder", None)
        batches = [b for po in purchase_orders for b in self.store.traverse("PurchaseOrder", po["orderId"], "generatedFrom", None)]
        plans = [p for b in batches for p in self.store.traverse("AllocationBatch", b["batchId"], "belongsToPlan", None)]
        return {
            "order": order,
            "customer": self.store.traverse("Order", order["orderId"], "customer", None),
            "material": self.store.traverse("Order", order["orderId"], "material", None),
            "supplier": self.store.traverse("Order", order["orderId"], "supplier", None),
            "originalPurchaseOrder": purchase_orders,
            "allocationBatches": batches, "allocationPlans": plans,
            "supplierScores": self.store.query("SupplierScore", {"supplierId": order["supplierId"]}, None),
            "path": ["Order.customer", "Order.material", "Order.supplier", "Order.originalPurchaseOrder"],
        }

    def compare_options(self, params):
        self.require("Material", params["materialId"])
        candidates = self.store.query("SupplyOption", {"materialId": params["materialId"], "sourceSupplierId": params["supplierId"]}, None)
        results = [self.assess_option({**params, "optionId": o["optionId"]}) for o in candidates]
        for result in results:
            result.pop("orders", None)
            result.pop("snapshot", None)
        return {"supplierId": params["supplierId"], "materialId": params["materialId"],
                "options": sorted(results, key=lambda r: (not r["feasible"], r["extraCost"])),
                "method": "同物料、覆盖全部受影响需求；先检查约束，再按增量成本排序；不是AI预测或全局最优排产。"}

    def overview(self, params):
        kinds = ["Supplier", "Material", "Customer", "Order", "SupplyOption",
                 "AllocationPlan", "AllocationBatch", "PurchaseOrder", "SupplierScore"]
        counts = {kind: self.store.count(kind, {}) for kind in kinds}
        impacts = [self.assess_delay({"supplierId": s["supplierId"]})
                   for s in self.store.query("Supplier", {}, None) if s.get("delayDays", 0) > 0]
        return {"counts": counts, "affectedSalesAmount": sum(i["affectedSalesAmount"] for i in impacts),
                "affectedOrderCount": sum(len(i["orderIds"]) for i in impacts),
                "delayedSuppliers": [{k: v for k, v in i.items() if k != "orders"} for i in impacts],
                "inventory": [{"materialId": m["materialId"], "name": m["name"],
                               "currentStock": m["currentStock"], "reservedStock": m["reservedStock"],
                               "availableStock": m["currentStock"] - m["reservedStock"]}
                              for m in self.store.query("Material", {}, None)],
                "snapshotDate": "2026-07-01", "note": "所有数据均为教学数据；采购历史和销售需求分别计数，不相加为同一种订单。"}

    def aggregate_orders(self, params):
        """Whitelisted grouping; sales and purchasing are always separate scopes."""
        kind = params.get("objectType", "Order")
        group = params.get("groupBy", "supplierId")
        valid_groups = {"supplierId": ("Supplier", "name"), "materialId": ("Material", "name"),
                        "status": None}
        if kind == "Order":
            valid_groups["customerId"] = ("Customer", "name")
        if kind not in ("Order", "PurchaseOrder") or group not in valid_groups:
            raise KeyError("仅支持 Order/PurchaseOrder 按 supplierId、materialId、status 分组；销售订单还支持 customerId")
        filters = params.get("filters") or {}
        if not isinstance(filters, dict) or set(filters) - set(valid_groups):
            raise KeyError("filters 仅支持供应商、物料、状态和销售客户编号的等值筛选")
        if any(not isinstance(value, str) for value in filters.values()):
            raise KeyError("筛选值必须为字符串")
        affected_only = params.get("affectedOnly", False)
        if not isinstance(affected_only, bool) or (affected_only and kind != "Order"):
            raise KeyError("affectedOnly 仅支持销售订单，值必须为布尔值")
        limit = params.get("topN", 20)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise KeyError("topN 必须是1到100的整数")
        orders = self.store.query(kind, filters, None)
        if affected_only:
            orders = [o for o in orders if o["status"] == "open" and
                      self.require("Supplier", o["supplierId"])["delayDays"] > o["bufferDays"]]
        amount_key = "salesAmount" if kind == "Order" else "totalAmount"
        buckets = {}
        for order in orders:
            key = order[group]
            row = buckets.setdefault(key, {"key": key, "count": 0, "quantity": 0, "amount": Decimal(0)})
            row["count"] += 1
            row["quantity"] += order["quantity"]
            row["amount"] += Decimal(str(order[amount_key]))
        rows = []
        for key, row in buckets.items():
            target = valid_groups[group]
            row["label"] = f"{self.require(target[0], key)[target[1]]} ({key})" if target else key
            row["amount"] = float(row["amount"])
            rows.append(row)
        rows.sort(key=lambda row: (-row["amount"], row["key"]))
        return {"objectType": kind, "groupBy": group, "filters": filters, "affectedOnly": affected_only,
                "amountField": amount_key, "currency": "CNY", "rows": rows[:limit],
                "totalGroups": len(rows), "shownGroups": min(limit, len(rows)),
                "totals": {"count": len(orders), "quantity": sum(o["quantity"] for o in orders),
                           "amount": float(sum((Decimal(str(o[amount_key])) for o in orders), Decimal(0)))},
                "note": "按金额降序；合计覆盖全部筛选记录，Top N仅截取展示行。销售额/采购额分别计算；受影响销售额不是已发生损失。"}

    def validate_action(self, role, name, params):
        allowed = {
            "submitSupplierChange": {"buyer", "admin"},
            "approveSupplierChange": {"approver", "admin"},
            "executeSupplierChange": {"buyer", "admin"},
        }
        if role not in allowed.get(name, set()):
            raise PermissionError(f"角色 {role} 无权执行 {name}")
        if name == "submitSupplierChange":
            assessment = self.assess_option(params)
        else:
            request = self.require("ChangeRequest", params["requestId"])
            required_status = "pending" if name == "approveSupplierChange" else "approved"
            if request["status"] != required_status:
                raise KeyError(f"申请状态必须为 {required_status}，当前为 {request['status']}")
            assessment = self.assess_option(request)
            if assessment["snapshot"] != request["snapshot"]:
                raise KeyError("订单、供货方案或预算已变化，请重新提交并审批")
        if not assessment["feasible"]:
            raise KeyError("；".join(assessment["reasons"]))
        return assessment

    def execute(self, role, user_id, name, params, confirmed):
        if not confirmed:
            raise PermissionError("修改前需要用户确认")
        # Original ObjectStore commits every write separately. Use one SQLite
        # transaction so a multi-order change cannot be partially committed.
        if self.store._in_memory is not None:
            return self._execute(role, user_id, name, params)
        with closing(sqlite3.connect(self.store._db_path)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            fork = self.store.fork()
            result = SupplierService(fork)._execute(role, user_id, name, params)
            for kind, rows in fork._in_memory.items():
                for key, obj in rows.items():
                    if self.store.get(kind, key) != obj:
                        conn.execute("INSERT OR REPLACE INTO objects VALUES (?,?,?)",
                                     (kind, key, json.dumps(obj, ensure_ascii=False)))
            return result

    def _execute(self, role, user_id, name, params):
        assessment = self.validate_action(role, name, params)
        now = datetime.now(timezone.utc).isoformat()
        if name == "submitSupplierChange":
            request = {
                "requestId": f"CR-{uuid.uuid4().hex[:8]}", "status": "pending",
                "supplierId": params["supplierId"], "optionId": params["optionId"],
                "materialId": assessment["materialId"],
                "orderIds": assessment["orderIds"], "extraCost": assessment["extraCost"],
                "snapshot": assessment["snapshot"], "createdBy": user_id, "createdAt": now,
            }
            result = self.store.create("ChangeRequest", request)
        elif name == "approveSupplierChange":
            request = self.require("ChangeRequest", params["requestId"])
            if request["createdBy"] == user_id:
                raise PermissionError("提交人与审批人必须不同")
            result = self.store.update("ChangeRequest", request["requestId"],
                                       {"status": "approved", "approvedBy": user_id, "approvedAt": now})
        else:
            request = self.require("ChangeRequest", params["requestId"])
            for order in assessment["orders"]:
                self.store.update("Order", order["orderId"], {
                    "supplierId": assessment["replacementSupplierId"],
                    "lastChangeRequestId": request["requestId"],
                    "supplyOptionId": request["optionId"],
                })
            option = self.require("SupplyOption", request["optionId"])
            self.store.update("SupplyOption", option["optionId"], {
                "availableQuantity": option["availableQuantity"] - assessment["requiredQuantity"],
            })
            policy = self.require("Policy", "PROCUREMENT")
            remaining = Decimal(str(policy["extraBudget"])) - Decimal(str(assessment["extraCost"]))
            self.store.update("Policy", "PROCUREMENT", {"extraBudget": float(remaining)})
            result = self.store.update("ChangeRequest", request["requestId"], {
                "status": "executed", "executedBy": user_id, "executedAt": now,
            })
        return {"status": "executed", "action": name, "result": result}
