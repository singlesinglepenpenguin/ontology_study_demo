"""Make real DeepSeek calls and assert that the native agent uses runtime tools."""
import json
from pathlib import Path
import tempfile

from run import HERE, load_env, get_llm
from runtime import build_runtime
from ontopilot.agent import run_turn


def main():
    load_env()
    llm = get_llm()
    cases = [
        ("impact", "供应商S1延期，哪些销售订单受影响？请先查供应商和订单，再调用assessSupplierDelay，列出订单编号、销售金额与总需求。", "assessSupplierDelay", ["O1", "O2"]),
        ("option", "查询供货选项OPT-S2-P1，再调用assessSupplyOption评估它能否替代S1，额外成本是多少？预算改为1000元又如何？只评估，不提交申请。", "assessSupplyOption", ["2000"]),
        ("relations", "调用traceOrderRelations，沿O1的关系查出客户、商品、供应商，并列出它们的编号。", "traceOrderRelations", ["C1", "P1", "S1"]),
    ]
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        runtime = build_runtime(Path(tmp) / "live.db")
        for label, question, function, expected in cases:
            result = run_turn(runtime, llm, runtime._schema, runtime._governance,
                              "viewer-live", "viewer", "", question)
            events = result["trace_events"]
            used = [e["name"] for e in events if e["status"] == "success"]
            if f"function:{function}" not in used:
                raise AssertionError(f"{label}: 没有实际调用所需函数")
            normalized = result["response"].replace(",", "").replace("，", "")
            if not all(token in normalized for token in expected):
                raise AssertionError(f"{label}: 回答缺少预期对象或数值")
            results.append({"case": label, "question": question, **result})
            print(f"PASS {label}: {used}", flush=True)
    folder = HERE / "results"
    folder.mkdir(exist_ok=True)
    (folder / "live.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print("真实模型问答及工具轨迹已保存到 results/live.json")


if __name__ == "__main__":
    main()
