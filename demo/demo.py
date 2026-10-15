"""原创教学示例：无网络、无依赖；规则模拟决策流程，不调用大模型。"""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone


def seed():
    return {
        "suppliers": {
            "S1": {"name": "原供应商", "delay_days": 7},
            "S2": {"name": "备选供应商", "delay_days": 0, "stock": 100,
                   "extra_unit_cost_yuan": 20, "approved": True},
        },
        "orders": [
            {"id": "O1", "customer": "客户甲", "supplier": "S1", "qty": 60,
             "sales_yuan": 60000, "gross_margin_rate": 0.30, "buffer_days": 3},
            {"id": "O2", "customer": "客户乙", "supplier": "S1", "qty": 40,
             "sales_yuan": 40000, "gross_margin_rate": 0.30, "buffer_days": 5},
        ],
        "audit": [],
    }


def propose(state, budget):
    affected = [o for o in state["orders"]
                if state["suppliers"][o["supplier"]]["delay_days"] > o["buffer_days"]]
    qty = sum(o["qty"] for o in affected)
    alt = state["suppliers"]["S2"]
    cost = qty * alt["extra_unit_cost_yuan"]
    feasible = bool(affected) and alt["approved"] and qty <= alt["stock"] and cost <= budget
    return {"order_ids": [o["id"] for o in affected], "target_supplier": "S2",
            "qty": qty, "affected_sales_yuan": sum(o["sales_yuan"] for o in affected),
            "affected_gross_profit_yuan": round(sum(o["sales_yuan"] * o["gross_margin_rate"] for o in affected)),
            "extra_cost_yuan": cost, "budget_yuan": budget, "feasible": feasible}


def apply_action(state, proposal, role, approved):
    if role != "manager" or not approved:
        raise ValueError("操作被拒绝：需要经理角色与显式审批。")
    fresh = propose(state, proposal["budget_yuan"])
    if fresh != proposal or not fresh["feasible"]:
        raise ValueError("操作被拒绝：方案过期、无待处理订单、库存不足或超出预算。")
    before = {o["id"]: o["supplier"] for o in state["orders"] if o["id"] in proposal["order_ids"]}
    for order in state["orders"]:
        if order["id"] in proposal["order_ids"]:
            order["supplier"] = proposal["target_supplier"]
    state["suppliers"]["S2"]["stock"] -= proposal["qty"]
    state["audit"].append({"time": datetime.now(timezone.utc).isoformat(), "actor_role": role,
                           "action": "switch_supplier", "before": before, "proposal": proposal})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path(__file__).with_name("state.json"))
    parser.add_argument("--budget", type=int, default=3000)
    parser.add_argument("--role", choices=["analyst", "manager"], default="analyst")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()
    state = json.loads(args.state.read_text()) if args.state.exists() else seed()
    proposal = propose(state, args.budget)
    print("【规则模拟；未调用大模型】查询关系 → 计算金额 → 生成方案")
    print(json.dumps(proposal, ensure_ascii=False, indent=2))
    if args.approve:
        try:
            apply_action(state, proposal, args.role, args.approve)
        except ValueError as error:
            parser.exit(1, str(error) + "\n")
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        print("已更新本地订单并记录审计：", args.state)
    else:
        print("仅展示提案，没有修改订单。受影响销售额不等于实际损失。")


if __name__ == "__main__":
    main()
