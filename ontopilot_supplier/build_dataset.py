"""Merge upstream procurement records with the delay lesson, deterministically.

No model calls. Every generated record declares its origin. Existing upstream
IDs and fields survive; the old S1/P1 lesson maps to SUP-001/MAT-001.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml
from run import HERE


def prop(description, kind="string"):
    return {"type": kind, "description": description}


def build():
    native = yaml.safe_load((HERE / "config/procurement_ontology.yaml").read_text())
    source = yaml.safe_load((HERE / "config/procurement_seed.yaml").read_text())
    extension = yaml.safe_load((HERE / "model/supplier_extension.yaml").read_text())
    schema = {"object_types": copy.deepcopy(native["object_types"]),
              "functions": copy.deepcopy(extension["functions"]), "actions": extension["actions"]}
    for kind, definition in extension["object_types"].items():
        if kind in schema["object_types"]:
            schema["object_types"][kind]["properties"].update(definition["properties"])
        else:
            schema["object_types"][kind] = definition
    schema["functions"]["analyzeSupplyRisk"] = native["functions"]["analyzeSupplyRisk"]
    schema["functions"]["analyzeSupplyRisk"]["description"] += "；沿用上游确定性评分规则，不是机器学习预测"
    schema["object_types"]["Material"]["properties"]["reservedStock"] = prop("已预留库存，不可供本轮新增需求使用", "integer")
    for definition in schema["object_types"].values():
        definition["properties"]["dataOrigin"] = prop("upstream 原项目教学记录；mock 本轮新增教学记录")

    seed = copy.deepcopy(source)
    for kind, rows in seed.items():
        for row in rows:
            row["dataOrigin"] = "upstream"
    delays = [7, 3, 0, 5, 0]
    for supplier, delay in zip(seed["Supplier"], delays):
        supplier["delayDays"] = delay
    for index, name, region, capacity, status in [
        (6, "南湾电源", "华南", 4500, "active"),
        (7, "东辰光电", "华东", 3200, "active"),
        (8, "停供测试商", "华北", 1500, "inactive"),
    ]:
        seed["Supplier"].append({"supplierId": f"SUP-{index:03}", "name": name,
            "region": region, "capacity": capacity, "yieldRate": .99,
            "deliveryTimeliness": .97, "qualityScore": 94, "priceIndex": 110,
            "leadTimeDays": 5, "certLevel": "A", "status": status,
            "delayDays": 0, "dataOrigin": "mock"})
        seed["SupplierScore"].append({"scoreId": f"SCORE-DEMO-{index}",
            "supplierId": f"SUP-{index:03}", "period": "2026-06",
            "deliveryScore": 97, "qualityScore": 94, "complianceScore": 95,
            "overallScore": 95.3, "evaluator": "demo", "dataOrigin": "mock"})

    seed.update({"Customer": [], "Order": [], "SupplyOption": [], "ChangeRequest": [],
                 "Policy": [{"policyId": "PROCUREMENT", "extraBudget": 30000, "dataOrigin": "mock"}]})
    for n in range(1, 13):
        seed["Customer"].append({"customerId": f"C{n}", "name": f"演示客户{n:02}",
                                 "region": ["华南", "华东", "华北"][(n-1) % 3], "dataOrigin": "mock"})
    origins = ["SUP-001", "SUP-002", "SUP-003", "SUP-004", "SUP-001", "SUP-005"]
    purchase_prices = [45, 88, 25, 150, 280, 3]
    sales_prices = [70, 135, 40, 210, 450, 5]
    # Different stories: feasible replacement, tight stock, no delay,
    # every alternative late, all complete alternatives over budget, healthy.
    profiles = [
        [("SUP-006", 1000, 20, True), ("SUP-004", 500, 10, True), ("SUP-002", 1400, 35, True), ("SUP-005", 2000, 5, False), ("SUP-008", 2000, 2, True), ("SUP-007", 1000, 28, True)],
        [("SUP-007", 500, 12, True), ("SUP-006", 200, 8, True), ("SUP-003", 600, 100, True), ("SUP-005", 1000, 5, False), ("SUP-008", 1000, 2, True), ("SUP-001", 600, 20, False)],
        [("SUP-006", 1000, 4, True), ("SUP-004", 300, 3, True), ("SUP-002", 800, 6, True), ("SUP-005", 1000, 2, False), ("SUP-008", 2000, 1, True), ("SUP-007", 800, 8, True)],
        [("SUP-007", 500, 12, False), ("SUP-002", 200, 8, True), ("SUP-006", 1000, 15, False), ("SUP-005", 1000, 5, False), ("SUP-008", 1000, 2, True), ("SUP-003", 100, 10, True)],
        [("SUP-006", 500, 180, True), ("SUP-002", 500, 160, True), ("SUP-005", 100, 20, True), ("SUP-004", 500, 10, False), ("SUP-008", 500, 2, True), ("SUP-007", 500, 200, True)],
        [("SUP-006", 10000, .5, True), ("SUP-004", 5000, .3, True), ("SUP-002", 8000, 1, True), ("SUP-001", 10000, .2, False), ("SUP-008", 20000, .1, True), ("SUP-007", 8000, .8, True)],
    ]
    anchors = [(600, 400, 200), (220, 180, 150), (100, 200, 150),
               (100, 200, 150), (80, 120, 100), (1000, 2000, 1500)]
    for m, material in enumerate(seed["Material"], 1):
        mid = material["materialId"]
        material["reservedStock"] = material["currentStock"] if m in (1, 2, 4, 5) else 0
        pid = f"PLAN-DEMO-{m:03}"
        base_quantity = 1000 if m != 6 else 5000
        origin_quantity = max(base_quantity, sum(anchors[m-1]) + 80)
        seed["AllocationPlan"].append({"planId": pid, "materialId": mid, "period": "2026-07",
            "totalQuantity": origin_quantity + base_quantity, "status": "executing",
            "strategy": "balanced", "note": "新增销售供货教学计划", "dataOrigin": "mock"})
        for slot, sid in enumerate([origins[m-1], "SUP-006"], 1):
            bid, poid = f"BATCH-DEMO-{m:03}-{slot}", f"PO-DEMO-{m:03}-{slot}"
            qty = origin_quantity if slot == 1 else base_quantity
            price = purchase_prices[m-1] + (0 if slot == 1 else profiles[m-1][0][2])
            seed["AllocationBatch"].append({"batchId": bid, "planId": pid, "supplierId": sid,
                "materialId": mid, "allocatedQty": qty, "confirmedQty": qty, "deliveredQty": 0,
                "unitPrice": price, "status": "confirmed", "dataOrigin": "mock"})
            seed["PurchaseOrder"].append({"orderId": poid, "batchId": bid, "supplierId": sid,
                "materialId": mid, "quantity": qty, "unitPrice": price, "totalAmount": qty * price,
                "orderDate": "2026-07-01", "deliveryDate": "2026-07-10", "status": "approved", "dataOrigin": "mock"})
        for j in range(8):
            oid = f"O{(m-1)*8+j+1}"
            qty = anchors[m-1][j] if j < 3 else 50 + 10*j
            supplier = origins[m-1] if j < 4 else "SUP-006"
            buffer = ([3, 5, 10, 12] if m in (1, 5) else [1, 2, 7, 8])[j] if j < 4 else 10
            seed["Order"].append({"orderId": oid, "customerId": f"C{((m-1)*2+j)%12+1}",
                "materialId": mid, "supplierId": supplier, "quantity": qty,
                "salesAmount": qty * sales_prices[m-1], "bufferDays": buffer,
                "status": "open" if j != 7 else "completed",
                "originalPurchaseOrderId": f"PO-DEMO-{m:03}-{1 if j < 4 else 2}", "dataOrigin": "mock"})
        for j, (sid, quantity, extra, on_time) in enumerate(profiles[m-1]):
            seed["SupplyOption"].append({"optionId": f"OPT-{mid}-{'FAST' if j == 0 else j+1}",
                "supplierId": sid, "sourceSupplierId": origins[m-1], "materialId": mid,
                "availableQuantity": quantity, "extraUnitCost": extra, "onTime": on_time, "dataOrigin": "mock"})

    seed["AllocationPlan"].append({"planId": "PLAN-DEMO-RISK", "materialId": "MAT-004", "period": "2026-07",
        "totalQuantity": 1800, "status": "draft", "strategy": "single_source",
        "note": "单一供应商且占用其90%月产能，供演示规则风险评分", "dataOrigin": "mock"})
    seed["AllocationBatch"].append({"batchId": "BATCH-DEMO-RISK", "planId": "PLAN-DEMO-RISK",
        "supplierId": "SUP-004", "materialId": "MAT-004", "allocatedQty": 1800,
        "confirmedQty": 0, "deliveredQty": 0, "unitPrice": 150, "status": "pending", "dataOrigin": "mock"})
    seed["PurchaseOrder"].append({"orderId": "PO-DEMO-RISK", "batchId": "BATCH-DEMO-RISK",
        "supplierId": "SUP-004", "materialId": "MAT-004", "quantity": 1800, "unitPrice": 150,
        "totalAmount": 270000, "orderDate": "2026-07-01", "deliveryDate": "2026-07-10", "status": "pending", "dataOrigin": "mock"})
    # Reject broken links instead of quietly loading inconsistent demonstration data.
    for kind, definition in schema["object_types"].items():
        rows = seed.get(kind, [])
        pk = next(k for k, v in definition["properties"].items() if v.get("primary_key"))
        assert len({r[pk] for r in rows}) == len(rows), kind
        for row in rows:
            for link in definition.get("links", {}).values():
                value = row.get(link["foreign_key"])
                if value is None:
                    continue
                target = schema["object_types"][link["target"]]
                target_pk = next(k for k,v in target["properties"].items() if v.get("primary_key"))
                valid = {r[target_pk] for r in seed.get(link["target"], [])}
                assert all(v in valid for v in (value if isinstance(value,list) else [value])), (kind, value)
    manifest = {"version": "procurement-merged-v2", "snapshotDate": "2026-07-01",
                "upstreamCommit": "dc9ac375b979c7ea4fa95d209194f55b10f909f9",
                "counts": {k: len(v) for k,v in seed.items()},
                "upstreamCounts": {k: len(v) for k,v in source.items()},
                "legacyMapping": {"S1": "SUP-001", "S2": "SUP-006", "S3": "SUP-004", "P1": "MAT-001", "P2": "MAT-002"},
                "mockFieldsOnUpstream": ["Supplier.delayDays", "Material.reservedStock"],
                "note": "原项目也为教学数据；增量价格相对sourceSupplierId报价；库存预留为新增假设；未接真实企业数据。"}
    for name, data in [("ontology_schema.yaml", schema), ("seed_data.yaml", seed)]:
        (HERE / "config" / name).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    manifest["seedSha256"] = hashlib.sha256((HERE / "config/seed_data.yaml").read_bytes()).hexdigest()
    (HERE / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest["counts"], ensure_ascii=False))


if __name__ == "__main__":
    build()
