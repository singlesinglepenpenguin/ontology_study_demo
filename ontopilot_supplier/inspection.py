"""Read-only inspection of the same object store used by the Agent."""
import json
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, Query, Request


def register_inspection(app):
    @app.get('/api/demo/model')
    async def model(request: Request):
        rt = request.app.state.runtime
        schema = rt._schema
        objects = []
        for name in schema.object_type_names:
            definition = schema.get_object_type(name)
            if not rt._governance.can_query('viewer', name):
                continue
            objects.append({'name': name, 'description': definition.description,
                            'count': rt._store.count(name, {}), 'primaryKey': definition.primary_key,
                            'properties': definition.properties,
                            'links': {key: {'target': link.target, 'foreignKey': link.foreign_key}
                                      for key, link in definition.links.items()}})
        return {'activeOntology': request.app.state.current_ontology_id,
                'autoLoaded': True, 'objects': objects,
                'functions': [{'name': name, 'description': schema.get_function(name).description}
                              for name in schema.function_names],
                'actions': [{'name': name, 'description': schema.get_action(name).description}
                            for name in schema.action_names]}

    @app.get('/api/demo/data')
    async def data(request: Request, object_type: str = 'Order', filters: str = '{}',
                   affected_only: bool = False, offset: int = Query(0, ge=0),
                   limit: int = Query(50, ge=1, le=200)):
        rt = request.app.state.runtime
        if object_type not in rt._schema.object_type_names:
            raise HTTPException(400, '未知对象类型')
        if not rt._governance.can_query('viewer', object_type):
            raise HTTPException(403, '该对象不在教学查询范围内')
        definition = rt._schema.get_object_type(object_type)
        try:
            parsed = json.loads(filters)
        except (ValueError, TypeError):
            raise HTTPException(400, '筛选条件必须是 JSON 字典')
        if not isinstance(parsed, dict) or set(parsed) - set(definition.properties):
            raise HTTPException(400, '筛选字段必须属于当前对象')
        if any(isinstance(value, (dict, list)) for value in parsed.values()):
            raise HTTPException(400, '仅支持字段等值筛选')
        if affected_only and object_type != 'Order':
            raise HTTPException(400, '延期影响筛选仅适用于销售订单 Order')
        # Fresh SQLite reads, no seed/config copy and no model-generated records.
        rows = rt._store.query(object_type, parsed, None)
        checks = {}
        if object_type == 'Order':
            suppliers = {s['supplierId']: s for s in rt._store.query('Supplier', {}, None)}
            for row in rows:
                delay = suppliers.get(row['supplierId'], {}).get('delayDays', 0)
                checks[row['orderId']] = {'delayDays': delay,
                    'affected': row.get('status') == 'open' and delay > row['bufferDays']}
            if affected_only:
                rows = [row for row in rows if checks[row['orderId']]['affected']]
        rows.sort(key=lambda row: str(row[definition.primary_key]))
        totals = {'count': len(rows)}
        if object_type in ('Order', 'PurchaseOrder'):
            amount_field = 'salesAmount' if object_type == 'Order' else 'totalAmount'
            totals.update(quantity=sum(row['quantity'] for row in rows), amountField=amount_field,
                          amount=float(sum((Decimal(str(row[amount_field])) for row in rows), Decimal(0))), currency='CNY')
        page = rows[offset:offset + limit]
        return {'objectType': object_type, 'primaryKey': definition.primary_key,
                'columns': list(definition.properties), 'filters': parsed, 'affectedOnly': affected_only,
                'rows': page, 'checks': {row[definition.primary_key]: checks[row[definition.primary_key]]
                                        for row in page if row[definition.primary_key] in checks},
                'totals': totals, 'offset': offset, 'limit': limit,
                'readAt': datetime.now(timezone.utc).isoformat(),
                'source': '当前 Agent 使用的 SQLite objects 表；按对象类型读取 JSON 记录。',
                'checkRule': '核对列为程序派生：status=open 且供应商 delayDays > 订单 bufferDays；原始记录单独展示。'}
