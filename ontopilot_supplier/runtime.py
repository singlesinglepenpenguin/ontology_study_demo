"""Use OntoPilot's real schema, store, governance, tracing and agent runtime."""
from __future__ import annotations

import json
from pathlib import Path

from ontopilot.actions import ActionExecutor
from ontopilot.audit import AuditLogger
from ontopilot.context import ContextBuilder
from ontopilot.functions import FunctionRegistry, FUNCTION_PARAMS
from ontopilot.governance import PermissionEvaluator
from ontopilot.runtime import OntologyRuntime
from ontopilot.schema import SchemaRegistry
from ontopilot.store import ObjectStore

from domain import SupplierService

HERE = Path(__file__).resolve().parent
DEFAULT_DB = HERE / ".procurement-v2.db"


class SupplierActions(ActionExecutor):
    def __init__(self, schema, store, governance):
        super().__init__(schema, store, governance)
        self.service = SupplierService(store)

    def preview(self, role, action_name, params):
        assessment = self.service.validate_action(role, action_name, params)
        return {"status": "pending_confirmation", "action": action_name,
                "target": params.get("requestId", "new ChangeRequest"),
                "changes": [{"action": action_name, "orderIds": assessment["orderIds"]}],
                "estimated_impact": {"extraCost": assessment["extraCost"]},
                "snapshot": assessment["snapshot"],
                "requires_confirmation": True}

    def execute(self, role, user_id, action_name, params, confirmed):
        params = dict(params)
        snapshot = params.pop("_confirmedSnapshot", None)
        return self.service.execute(role, user_id, action_name, params, confirmed,
                                    expected_snapshot=snapshot)


class SupplierContext(ContextBuilder):
    def __init__(self, path, store, governance, schema):
        super().__init__(path, store, governance)
        self.schema = schema

    def build(self, user_id, role, warehouse_id):
        text = super().build(user_id, role, warehouse_id)
        definitions = {}
        for name in self.schema.object_type_names:
            if not self._pe.can_query(role, name):
                continue
            obj = self.schema.get_object_type(name)
            definitions[name] = {
                "description": obj.description, "properties": obj.properties,
                "links": {k: {"target": v.target, "foreign_key": v.foreign_key}
                          for k, v in obj.links.items()},
            }
        return text + "\n[业务定义]\n" + json.dumps(definitions, ensure_ascii=False) + (
            "\n[教学范围]所有数据为虚构。金额单位为人民币元，数量为件。"
            "Order是客户销售订单，PurchaseOrder是采购单，不混合金额口径。"
            "本例按原物料规格直接转售，一单一物料，不模拟生产BOM。"
            "原始采购数据与新增销售需求共享Supplier和Material编号。"
            "请先 object_query 查询 Supplier、Order，再 call_function 计算。"
            "客户与订单按 customerId 关联，供货选项按 materialId 和 sourceSupplierId 关联。"
            "assessSupplierDelay 计算影响，assessSupplyOption 评估供货选项。"
            "traceOrderRelations 实际沿订单关系查客户、物料、供应商、历史采购单和评分。"
            "分组汇总、排名、图表调用aggregateOrders，严禁用object_query的aggregation参数做sum/group_by。"
            "全局概览调用getProcurementOverview；候选方案比较调用compareSupplyOptions。"
            "analyzeSupplyRisk是上游规则评分，不是AI预测。"
            "该风险函数未定义100分满分，不要补写/100或把分数换成概率。"
            "assessSupplyOption只替换选项对应物料的受影响订单，不能跨物料相加选型。"
            "库存须减去reservedStock；本例风险物料可用库存为0，不做库存分摊或排产。"
            "回答须列出具体对象编号和工具返回的计算依据。"
            "评估和推荐不会自动创建申请；提交、审批、执行是不同操作。"
            "缺少信息时查询，不编造。不要调用物流仿真工具，本场景无 Shipment。"
        )


def build_runtime(db_path=None, reset=False):
    config = HERE / "config"
    schema = SchemaRegistry(str(config / "ontology_schema.yaml"))
    store = ObjectStore(str(db_path or DEFAULT_DB), schema)
    if reset:
        store.clear_all()
    if not store.count("Supplier", {}):
        store.load_seed_data(str(config / "seed_data.yaml"))
    governance = PermissionEvaluator(str(config / "permissions.yaml"))
    functions = FunctionRegistry(schema, store)
    service = SupplierService(store)
    functions._fns.update({
        "assessSupplierDelay": service.assess_delay,
        "assessSupplyOption": service.assess_option,
        "getChangeRequest": service.request_details,
        "traceOrderRelations": service.trace_order,
        "getProcurementOverview": service.overview,
        "compareSupplyOptions": service.compare_options,
        "aggregateOrders": service.aggregate_orders,
    })
    for name in schema.function_names:
        definition = schema.get_function(name)
        FUNCTION_PARAMS[name] = {
            "description": definition.description,
            "required": {k: v.get("description", k) for k, v in definition.params.items() if v.get("required")},
            "optional": {k: v.get("description", k) for k, v in definition.params.items() if not v.get("required")},
        }
    audit = AuditLogger(str(db_path or DEFAULT_DB))
    runtime = OntologyRuntime(
        schema, store, governance,
        SupplierContext(str(config / "context_sources.yaml"), store, governance, schema),
        functions, SupplierActions(schema, store, governance), audit,
    )
    return runtime
