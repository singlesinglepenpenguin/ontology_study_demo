import React, { useEffect, useState } from 'react'
import { ModelInfo } from './SupplierOntologyPanel'

type RecordRow = Record<string, unknown>
interface DataPage {
  objectType: string; primaryKey: string; columns: string[]; rows: RecordRow[]
  checks: Record<string, { delayDays: number; affected: boolean }>
  totals: { count: number; quantity?: number; amount?: number; amountField?: string }
  readAt: string; source: string; checkRule: string; offset: number; limit: number
}
const names: Record<string, string> = { Order: '客户销售订单', PurchaseOrder: '采购单', Supplier: '供应商', Material: '物料', Customer: '客户', SupplyOption: '备选供货报价', Policy: '预算策略', ChangeRequest: '变更申请', AllocationPlan: '分货计划', AllocationBatch: '分货批次', SupplierScore: '供应商评分' }
const labels: Record<string, string> = { orderId: '订单编号', customerId: '客户', supplierId: '供应商', materialId: '物料', quantity: '数量（件）', salesAmount: '销售金额（元）', totalAmount: '采购金额（元）', bufferDays: '容忍延期（天）', status: '状态', originalPurchaseOrderId: '原采购单', dataOrigin: '数据来源', delayDays: '延期天数', extraBudget: '剩余预算', extraUnitCost: '每件增量成本', availableQuantity: '可供数量', optionId: '报价编号', sourceSupplierId: '原供应商', onTime: '能否准时' }
export function SupplierDataPanel() {
  const [model, setModel] = useState<ModelInfo | null>(null)
  const [query, setQuery] = useState({ kind: 'Order', filters: {} as Record<string, unknown>, affected: false, offset: 0 })
  const [field, setField] = useState('supplierId'), [value, setValue] = useState('')
  const [revision, setRevision] = useState(0)
  const [data, setData] = useState<DataPage | null>(null), [selected, setSelected] = useState<RecordRow | null>(null)
  const [error, setError] = useState(''), [loading, setLoading] = useState(false)
  useEffect(() => { const controller = new AbortController(); fetch('/api/demo/model', { signal: controller.signal }).then(async r => { if (!r.ok) throw new Error('读取对象列表失败'); return r.json() }).then(setModel).catch(e => { if (e.name !== 'AbortError') setError(e.message) }); return () => controller.abort() }, [])
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(''); setData(null); setSelected(null)
    const params = new URLSearchParams({ object_type: query.kind, filters: JSON.stringify(query.filters), affected_only: String(query.affected), offset: String(query.offset), limit: '25' })
    fetch('/api/demo/data?' + params, { signal: controller.signal }).then(async r => { const body = await r.json(); if (!r.ok) throw new Error(body.detail || '读取记录失败'); return body }).then(setData).catch(e => { if (e.name !== 'AbortError') setError(e.message) }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [query, revision])
  const definition = model?.objects.find(object => object.name === query.kind)
  function preset(filters: Record<string, unknown>, affected: boolean) { setQuery({ kind: 'Order', filters, affected, offset: 0 }); setField('supplierId'); setValue('') }
  function addFilter(event: React.FormEvent) {
    event.preventDefault(); if (!value.trim()) return
    const type = definition?.properties[field]?.type
    let parsed: unknown = value.trim()
    if (type === 'number' || type === 'integer') { parsed = Number(value); if (!Number.isFinite(parsed)) { setError('请输入有效数字'); return } }
    if (type === 'boolean') { if (!['true', 'false'].includes(value.trim())) { setError('布尔值请填写 true 或 false'); return }; parsed = value.trim() === 'true' }
    setQuery(prev => ({ ...prev, offset: 0, filters: { ...prev.filters, [field]: parsed } })); setValue('')
  }
  return <div className="h-full overflow-y-auto p-6 space-y-4">
    <div className="flex items-start justify-between gap-4"><div><h1 className="text-xl font-semibold">数据明细</h1><p className="text-sm text-gray-500 mt-2">直接读取 Agent 使用的当前 SQLite 业务记录。可以按相同条件筛选，再对照对话中的「实际工具返回」。</p></div><button className="border rounded px-3 py-2 text-sm bg-white" onClick={() => setRevision(n => n + 1)}>刷新数据</button></div>
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm leading-relaxed">
      <strong>先对齐统计范围：</strong>电芯受影响为 O1、O2（70,000 元）；华兴科技全部受影响还包括芯片 O33、O34（共 160,000 元）；所有供应商、所有物料受影响共 277,000 元。这是初始快照口径，下面金额以当前数据库为准。
      <div className="flex flex-wrap gap-2 mt-3">{([
        ['电芯受影响', { supplierId: 'SUP-001', materialId: 'MAT-001' }, true],
        ['电芯全部订单', { materialId: 'MAT-001' }, false],
        ['华兴全部受影响', { supplierId: 'SUP-001' }, true],
        ['全部受影响', {}, true],
      ] as [string, Record<string, unknown>, boolean][]).map(([label, filters, affected]) => <button key={label} className="px-3 py-1.5 border border-blue-300 bg-white rounded text-blue-700" onClick={() => preset(filters, affected)}>{label}</button>)}</div>
    </div>
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <label>对象类型 <select aria-label="对象类型" className="border rounded px-2 py-2 ml-2 bg-white" value={query.kind} onChange={e => { const kind = e.target.value; setQuery({ kind, filters: {}, affected: false, offset: 0 }); setField(model?.objects.find(o => o.name === kind)?.primaryKey || ''); setValue('') }}>{model?.objects.map(object => <option key={object.name} value={object.name}>{names[object.name] || object.name} · {object.name}</option>)}</select></label>
      {query.kind === 'Order' && <label className="flex items-center gap-2"><input type="checkbox" checked={query.affected} onChange={e => setQuery(prev => ({ ...prev, affected: e.target.checked, offset: 0 }))} />只看受延期影响</label>}
      <button className="text-blue-600" onClick={() => setQuery(prev => ({ ...prev, filters: {}, affected: false, offset: 0 }))}>清除筛选</button>
    </div>
    <form onSubmit={addFilter} className="flex flex-wrap gap-2 text-sm"><select aria-label="筛选字段" className="border rounded p-2" value={field} onChange={e => setField(e.target.value)}>{Object.keys(definition?.properties || {}).map(key => <option key={key} value={key}>{labels[key] || key} · {key}</option>)}</select><input aria-label="筛选值" placeholder="等于，例如 SUP-001" className="border rounded p-2" value={value} onChange={e => setValue(e.target.value)} /><button className="bg-blue-600 text-white px-3 py-2 rounded" disabled={!value.trim()}>添加筛选</button></form>
    <div className="flex flex-wrap gap-2 text-xs">{Object.entries(query.filters).map(([key, val]) => <button key={key} className="px-2 py-1 border rounded bg-white" onClick={() => setQuery(prev => { const filters = { ...prev.filters }; delete filters[key]; return { ...prev, filters, offset: 0 } })}>{key} = {String(val)} ×</button>)}</div>
    {error && <p role="alert" className="text-red-600">{error}</p>}
    {loading && <p>正在读取当前数据库…</p>}
    {data && <>
      <div data-testid="data-totals" className="rounded-lg border bg-white p-4 text-sm"><strong>全部筛选记录合计：{data.totals.count} 条</strong>{data.totals.quantity !== undefined && <> · {data.totals.quantity.toLocaleString()} 件 · {data.totals.amountField === 'salesAmount' ? '销售额' : '采购额'} ¥{data.totals.amount?.toLocaleString()}</>}<p className="text-xs text-gray-500 mt-2">合计覆盖当前全部筛选记录，不仅是本页。读取时间：{new Date(data.readAt).toLocaleString('zh-CN')}</p></div>
      <p className="text-xs text-gray-500">{data.source} {query.kind === 'Order' && data.checkRule}</p>
      <div className="border rounded-lg bg-white overflow-x-auto"><table className="text-xs w-full whitespace-nowrap" data-testid="data-records"><thead className="bg-gray-100 text-left"><tr><th className="p-3">原始记录</th>{data.columns.map(key => <th key={key} className="p-3" title={definition?.properties[key]?.description}>{labels[key] || key}<div className="font-normal text-gray-400">{key}</div></th>)}{query.kind === 'Order' && <><th className="p-3">供应商延期<br />（核对列）</th><th className="p-3">是否受影响<br />（核对列）</th></>}</tr></thead><tbody>{data.rows.map(row => <tr key={String(row[data.primaryKey])} className="border-t hover:bg-blue-50"><td className="p-3"><button className="text-blue-600" onClick={() => setSelected(row)}>查看 JSON</button></td>{data.columns.map(key => <td key={key} className="p-3" title={typeof row[key] === 'object' ? JSON.stringify(row[key]) : String(row[key] ?? '')}>{typeof row[key] === 'object' ? JSON.stringify(row[key]) : String(row[key] ?? '—')}</td>)}{query.kind === 'Order' && <><td className="p-3">{data.checks[String(row[data.primaryKey])]?.delayDays} 天</td><td className="p-3">{data.checks[String(row[data.primaryKey])]?.affected ? '受影响' : '不受影响'}</td></>}</tr>)}</tbody></table>{!data.rows.length && <p className="p-6 text-gray-500 text-sm">没有匹配记录</p>}</div>
      <div className="flex gap-4 items-center text-sm"><button className="border rounded px-3 py-1 bg-white disabled:opacity-40" disabled={data.offset === 0} onClick={() => setQuery(prev => ({ ...prev, offset: Math.max(0, prev.offset - data.limit) }))}>上一页</button><span>第 {Math.floor(data.offset / data.limit) + 1} 页 · 本页 {data.rows.length} 条</span><button className="border rounded px-3 py-1 bg-white disabled:opacity-40" disabled={data.offset + data.limit >= data.totals.count} onClick={() => setQuery(prev => ({ ...prev, offset: prev.offset + data.limit }))}>下一页</button></div>
      {selected && <section className="bg-slate-900 text-slate-100 rounded-lg p-4" data-testid="record-json"><div className="flex justify-between"><h2>SQLite 中保存的记录 JSON · {String(selected[data.primaryKey])}</h2><button onClick={() => setSelected(null)}>关闭</button></div><pre className="text-xs mt-3 overflow-auto">{JSON.stringify(selected, null, 2)}</pre></section>}
    </>}
  </div>
}
