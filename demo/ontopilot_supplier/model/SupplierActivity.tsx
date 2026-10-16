import React from 'react'

export interface AggregateView {
  objectType: string; amountField: string; groupBy: string; affectedOnly: boolean
  rows: { key: string; label: string; count: number; quantity: number; amount: number }[]
  totals: { count: number; quantity: number; amount: number }; totalGroups: number; shownGroups: number
}
export interface ToolResult { origin?: string; tool: string; arguments: Record<string, unknown>; result: unknown }
export function SupplierActivity({ steps, streaming, charts, toolResults }: { steps?: string[]; streaming?: boolean; charts?: AggregateView[]; toolResults?: ToolResult[] }) {
  return <>
    {!!steps?.length && <details open={streaming || undefined} className="mb-3 border rounded-lg bg-white p-3 text-xs" data-testid="execution-progress">
      <summary className="cursor-pointer text-blue-700">{streaming ? '正在处理' : '执行完成'} · 查看查询与计算步骤</summary>
      <p className="text-gray-400 mt-2">以下为实际执行状态与工具名称。</p>
      <ol className="mt-2 space-y-1 text-gray-600">{steps.map((step, i) => <li key={i}>{i + 1}. {step}</li>)}</ol>
    </details>}
    {!!toolResults?.length && <details className="mb-3 border rounded-lg bg-white p-3 text-xs" data-testid="tool-results">
      <summary className="cursor-pointer text-blue-700">实际工具返回（{toolResults.length} 次工具调用）</summary>
      <p className="text-gray-400 mt-2">这是工具实际返回给 Agent 的结果。可与左侧「数据明细」使用相同条件核对。</p>
      {toolResults.map((entry, index) => <details key={index} className="mt-2 border-t pt-2">
        <summary className="cursor-pointer font-mono">{index + 1}. {entry.origin ? entry.origin + ' · ' : ''}{String(entry.arguments.function_name || entry.arguments.object_type || entry.arguments.action_name || entry.tool)}</summary>
        <p className="mt-2 text-gray-500">调用参数</p><pre className="overflow-auto max-h-48 whitespace-pre-wrap mt-1">{JSON.stringify(entry.arguments, null, 2)}</pre>
        <p className="mt-2 text-gray-500">工具返回</p><pre className="overflow-auto max-h-80 whitespace-pre-wrap mt-1">{JSON.stringify(entry.result, null, 2)}</pre>
      </details>)}
    </details>}
    {charts?.map((chart, i) => {
      const max = Math.max(1, ...chart.rows.map(row => row.amount))
      const title = `${chart.objectType === 'Order' ? '销售订单' : '采购单'}${chart.affectedOnly ? ' · 受延期影响' : ''}`
      return <section key={i} className="my-3 p-4 border rounded-lg bg-white" data-testid="aggregate-view">
        <h3 className="font-semibold text-sm">{title} · 按 {({ supplierId: '供应商', materialId: '物料', customerId: '客户', status: '状态' } as Record<string, string>)[chart.groupBy] || chart.groupBy} 汇总</h3>
        <p className="text-xs text-gray-500 mt-1">全部筛选记录：{chart.totals.count} 单 · {chart.totals.quantity.toLocaleString()} 件 · ¥{chart.totals.amount.toLocaleString()}</p>
        {chart.rows.length === 0 ? <p className="text-sm mt-3">没有匹配记录</p> : <div className="overflow-x-auto"><table className="w-full text-xs mt-3">
          <thead><tr className="text-left text-gray-500"><th>分组 / 金额比例</th><th>单数</th><th>件数</th><th>金额（元）</th></tr></thead>
          <tbody>{chart.rows.map(row => <tr key={row.key} className="border-t"><td className="py-2 pr-3">
            {row.label}<div className="bg-slate-100 h-1.5 mt-1 rounded"><div className="bg-blue-500 h-1.5 rounded" style={{ width: `${row.amount / max * 100}%` }} /></div>
          </td><td>{row.count}</td><td>{row.quantity.toLocaleString()}</td><td>{row.amount.toLocaleString()}</td></tr>)}</tbody>
        </table></div>}
        <p className="text-xs text-gray-400 mt-2">按金额降序，展示 {chart.shownGroups}/{chart.totalGroups} 组。合计包含未展示的分组；金额来自计算工具。</p>
      </section>
    })}
  </>
}
