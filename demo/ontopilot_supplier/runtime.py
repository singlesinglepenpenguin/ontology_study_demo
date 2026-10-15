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
                "requires_confirmation": True}

    def execute(self, role, user_id, action_name, params, confirmed):
        return self.service.execute(role, user_id, action_name, params, confirmed)


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
            "订单为销售订单，一单一商品、单一供应商，省略采购单及排程。"
            "请先 object_query 查询 Supplier、Order，再 call_function 计算。"
            "客户与订单按 customerId 关联，供货选项按 productId 关联。"
            "assessSupplierDelay 计算影响，assessSupplyOption 评估供货选项。"
            "traceOrderRelations 实际沿订单关系查询客户、商品和供应商。"
            "回答须列出具体对象编号和工具返回的计算依据。"
            "评估和推荐不会自动创建申请；提交、审批、执行是不同操作。"
            "缺少信息时查询，不编造。不要调用物流仿真工具，本场景无 Shipment。"
        )


def build_runtime(db_path=None, reset=False):
    config = HERE / "config"
    schema = SchemaRegistry(str(config / "ontology_schema.yaml"))
    store = ObjectStore(str(db_path or HERE / ".ontopilot.db"), schema)
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
    })
    for name in schema.function_names:
        definition = schema.get_function(name)
        FUNCTION_PARAMS[name] = {
            "description": definition.description,
            "required": {k: v.get("description", k) for k, v in definition.params.items() if v.get("required")},
            "optional": {k: v.get("description", k) for k, v in definition.params.items() if not v.get("required")},
        }
    audit = AuditLogger(str(db_path or HERE / ".ontopilot.db"))
    runtime = OntologyRuntime(
        schema, store, governance,
        SupplierContext(str(config / "context_sources.yaml"), store, governance, schema),
        functions, SupplierActions(schema, store, governance), audit,
    )
    return runtime
