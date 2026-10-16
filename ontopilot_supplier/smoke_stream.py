"""Exercise real HTTP streaming + real DeepSeek, including multi-turn aggregation."""
import json
import time
from pathlib import Path
import httpx
import run
from runtime import build_runtime


def main():
    rt = build_runtime()
    cases = [
        ('sales-material', '把全部销售订单按物料汇总，展示金额排名图表、单数、件数和全量总计。', {'groupBy': 'materialId'}, False),
        ('sales-followup', '在刚才销售订单的口径下，只看MAT-001，改为按客户汇总，给出图表与总计。', {'groupBy': 'customerId', 'filters': {'materialId': 'MAT-001'}}, True),
        ('impact-supplier', '只统计受延期影响的销售订单，按供应商汇总，展示金额图表和全量总计。', {'groupBy': 'supplierId', 'affectedOnly': True}, False),
        ('purchase-top5', '采购单按供应商汇总金额前5名，展示图表、单数和全量合计，不要混入销售订单。', {'objectType': 'PurchaseOrder', 'groupBy': 'supplierId', 'topN': 5}, False),
        ('empty', '销售订单中只筛选供应商SUP-999，按物料汇总，展示图表和总计。不存在就如实说明，不要切换到其他供应商。', {'filters': {'supplierId': 'SUP-999'}, 'groupBy': 'materialId'}, False),
        ('delay', '华兴科技SUP-001的锂离子电芯MAT-001延期，影响哪些销售订单？对照未受影响订单，计算销售额和需求。', None, False),
    ]
    results, sid = {}, None
    with httpx.Client(timeout=180, trust_env=False) as client:
        client.post('http://127.0.0.1:8000/api/login', json={'username': 'viewer', 'password': 'demo123'}).raise_for_status()
        for name, question, params, follow in cases:
            start, events = time.monotonic(), []
            body = {'user_id': 'viewer-demo', 'role': 'viewer', 'warehouse_id': '', 'message': question}
            if follow: body['session_id'] = sid
            with client.stream('POST', 'http://127.0.0.1:8000/api/chat/live', json=body) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith('data: '):
                        event = json.loads(line[6:])
                        events.append({'at': round(time.monotonic() - start, 3), **event})
            assert not any(e['type'] == 'error' for e in events), events
            final = next(e for e in events if e['type'] == 'complete')
            sid = final['session_id']
            deltas = [e for e in events if e['type'] == 'answer_delta']
            assert len(deltas) > 1 and deltas[0]['at'] < final['at']
            assert events[0]['type'] == 'session' and events[1]['type'] == 'progress'
            if params is not None:
                charts = [e for e in events if e['type'] == 'visualization']
                expected = rt.call_function('v', 'viewer', 'aggregateOrders', params)
                assert any(all(chart.get(k) == expected[k] for k in ('objectType', 'groupBy', 'totals', 'rows')) for chart in charts), (name, charts, expected)
            else:
                assert 'O1' in final['response'] and 'O2' in final['response']
                assert any(e['name'] == 'function:assessSupplierDelay' for e in final['trace_events'])
            stored = client.get('http://127.0.0.1:8000/api/sessions/' + sid).json()['session']['messages'][-1]
            assert stored['content'] == final['response'] and stored['steps']
            if params is not None: assert stored['charts']
            results[name] = {'question': question, 'elapsed': final['at'], 'firstDelta': deltas[0]['at'],
                             'deltaCount': len(deltas), 'events': events, 'status': 'passed'}
            print(f'PASS {name}: {len(deltas)} deltas, first={deltas[0]["at"]}s, end={final["at"]}s', flush=True)
            output = Path(__file__).parent / 'results/stream.json'
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
