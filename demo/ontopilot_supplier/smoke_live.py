"""Make real DeepSeek calls and assert that the native agent uses runtime tools."""
import json
from pathlib import Path
import tempfile
import argparse

from run import HERE, load_env, get_llm
from runtime import build_runtime
from ontopilot.agent import run_turn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="仅重新验证指定问题，其他记录保留")
    args = parser.parse_args()
    load_env()
    llm = get_llm()
    cases = [
        ("overview", "给我采购业务全景，统计供应商、物料、销售订单和采购单数量，以及受影响订单数和销售额。", "getProcurementOverview", ["48", "18"]),
        ("impact", "华兴科技的锂离子电芯MAT-001延期，影响哪些销售订单？列出订单编号、销售额、需求量和未受影响的对照。只看这一物料。", "assessSupplierDelay", ["O1", "O2"]),
        ("option", "比较华兴科技SUP-001的锂离子电芯MAT-001所有备选方案，选出预算内能覆盖需求的方案，说明为什么最便宜的不一定能用。请列选项编号。只评估。", "compareSupplyOptions", ["OPT-MAT-001-FAST"]),
        ("late", "海威电子SUP-004的光学镜头MAT-004延期，有没有能完全覆盖需求且准时的备选供货方案？比较所有候选并列出不可行原因。", "compareSupplyOptions", ["MAT-004"]),
        ("budget", "华兴科技SUP-001的主控芯片MAT-005延期，比较全部供货选项，说明预算为什么不够，列出最低的可全量准时供货成本和预算。", "compareSupplyOptions", ["MAT-005"]),
        ("relations", "沿O1的业务关系查出客户、物料、供应商、最初采购单、分货批次和分货计划，列出各自编号，并看看供应商历史评分。", "traceOrderRelations", ["C1", "MAT-001", "PO-DEMO-001-1", "PLAN-DEMO-001"]),
        ("risk", "PLAN-DEMO-RISK为什么是高风险？算出风险分数，解释评分规则，不要当成AI预测概率。", "analyzeSupplyRisk", ["85"]),
    ]
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        runtime = build_runtime(Path(tmp) / "live.db")
        for label, question, function, expected in cases:
            if args.case and label != args.case:
                continue
            result = run_turn(runtime, llm, runtime._schema, runtime._governance,
                              "viewer-live", "viewer", "", question)
            events = result["trace_events"]
            used = [e["name"] for e in events if e["status"] == "success"]
            if f"function:{function}" not in used:
                raise AssertionError(f"{label}: 没有实际调用所需函数")
            normalized = result["response"].replace(",", "").replace("，", "")
            if not all(token in normalized for token in expected):
                raise AssertionError(f"{label}: 回答缺少预期对象或数值")
            if label == "risk" and ("/100" in normalized.replace(" ", "") or "满分100" in normalized):
                raise AssertionError("风险函数未定义100分满分，不得补造分母")
            results.append({"case": label, "question": question, **result})
            print(f"PASS {label}: {used}", flush=True)
    folder = HERE / "results"
    folder.mkdir(exist_ok=True)
    if args.case and (folder / "live.json").exists():
        old = json.loads((folder / "live.json").read_text())
        replacements = {r["case"]: r for r in results}
        results = [replacements.get(r["case"], r) for r in old]
    (folder / "live.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print("真实模型问答及工具轨迹已保存到 results/live.json")


if __name__ == "__main__":
    main()
