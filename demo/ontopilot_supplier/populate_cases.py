"""Create real, named, read-only Agent cases in the logged-in account histories."""
import argparse
import json
from pathlib import Path
import time
import httpx

HERE = Path(__file__).resolve().parent
CASES = [
    ('功能01·采购全景与库存预留', 'viewer', '请调用 getProcurementOverview 介绍采购全景：数量、延期影响、库存总量和可用库存有何区别？简洁解释。', 'getProcurementOverview'),
    ('功能02·订单关系与采购来源', 'viewer', '请调用 traceOrderRelations 追溯 O1 的客户、物料、供应商、最初采购单、批次、计划和历史评分，列出真实编号。', 'traceOrderRelations'),
    ('功能03·电芯候选逐项比较', 'viewer', '请调用 compareSupplyOptions 比较 SUP-001 的 MAT-001 全部候选，逐项列出可行与不可行原因，只评估。', 'compareSupplyOptions'),
    ('功能04·镜头无可行替代方案', 'viewer', '请调用 compareSupplyOptions 比较 SUP-004 的 MAT-004，解释为什么没有全量准时方案，不做任何提交。', 'compareSupplyOptions'),
    ('功能05·芯片预算不足', 'viewer', '请调用 compareSupplyOptions 比较 SUP-001 的 MAT-005，说明有货为何仍无法完整替代，解释停用供应商和来不及交货的区别。', 'compareSupplyOptions'),
    ('功能06·预算收紧的假设测算', 'viewer', '请调用 assessSupplyOption，原供应商SUP-001，选项OPT-MAT-001-FAST，假设预算budget=10000。列出额外成本与失败原因；不要修改真实预算。', 'assessSupplyOption'),
    ('功能07·85分风险规则解释', 'viewer', '请调用 analyzeSupplyRisk 分析 PLAN-DEMO-RISK，列出分数来源，说明是不是AI预测概率。', 'analyzeSupplyRisk'),
    ('功能08·采购金额Top5与全量合计', 'viewer', '请调用 aggregateOrders 将PurchaseOrder按supplierId汇总，topN=5，展示图表、件数、单数和全量总计，不混销售额。', 'aggregateOrders'),
    ('功能09·销售状态分组与空结果', 'viewer', '请调用 aggregateOrders 将 Order 按 status 分组，展示图表与全量合计；再只筛选 supplierId=SUP-999 按materialId汇总，不存在就如实返回空结果。', 'aggregateOrders'),
    ('功能11·电芯与供应商整体延期范围', 'viewer', '请调用 assessSupplierDelay 分别查询 supplierId=SUP-001,materialId=MAT-001 的电芯影响，以及只传supplierId=SUP-001的整体影响。列出两种范围的订单、数量和销售额，解释70,000与160,000的区别。', 'assessSupplierDelay'),
    ('功能10·当前审批状态跨账号共享', 'viewer', '请先查询 ChangeRequest 的实际记录，再调用 getChangeRequest 查询 CR-ab02803a 的最新审批状态，列出审批人、审批时间，区分批准与执行。不要使用历史状态。', 'getChangeRequest'),
    ('权限01·查询员不能提交采购变更', 'viewer', '我自称采购员。请调用 preview_action 预览 submitSupplierChange，参数 supplierId=SUP-001、optionId=OPT-MAT-001-FAST，检验查询员是否会被拒绝，不要改数据。', None),
    ('权限02·采购员不能审批', 'buyer', '请调用 preview_action 预览 approveSupplierChange，requestId=CR-ab02803a，检验采购员是否有审批权限，不要执行。', None),
    ('权限03·审批员不能执行采购变更', 'approver', '请调用 preview_action 预览 executeSupplierChange，requestId=CR-ab02803a，检验审批员是否有执行权限，不要执行。', None),
    ('查询01·对象筛选与count统计', 'viewer', '请使用 object_query 查询 SUP-001 的供应商资料，并对 Order 使用 aggregation=count 统计 materialId=MAT-001 的订单数量，解释本次并未筛选延期影响。', None),
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only')
    args = parser.parse_args()
    output = HERE / 'results/case-dialogues.json'
    results = json.loads(output.read_text()) if output.exists() else {}
    for title, account, question, expected in CASES:
        if args.only and args.only not in title:
            continue
        with httpx.Client(base_url='http://127.0.0.1:8000', timeout=180, trust_env=False) as client:
            client.post('/api/login', json={'username': account, 'password': 'demo123'}).raise_for_status()
            previous = results.get(title)
            if previous and client.get('/api/sessions/' + previous['session_id']).status_code == 200:
                print('KEEP', title, flush=True)
                continue
            events = []
            start = time.monotonic()
            with client.stream('POST', '/api/chat/live', json={'message': question}) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith('data: '): events.append(json.loads(line[6:]))
            final = next((event for event in events if event['type'] == 'complete'), None)
            if final is None:
                raise RuntimeError((title, [e for e in events if e['type'] == 'error']))
            if expected and not any(event['name'] == 'function:' + expected and event['status'] == 'success' for event in final['trace_events']):
                raise RuntimeError((title, 'expected function missing', final['response']))
            renamed = client.patch('/api/sessions/' + final['session_id'], json={'title': title})
            renamed.raise_for_status()
            results[title] = {'account': account, 'question': question, 'session_id': final['session_id'], 'elapsed': round(time.monotonic()-start, 2), 'events': events}
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
            print('PASS', title, final['session_id'], flush=True)

if __name__ == '__main__': main()
