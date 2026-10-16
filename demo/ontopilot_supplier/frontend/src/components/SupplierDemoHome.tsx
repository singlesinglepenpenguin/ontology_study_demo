import React, { useEffect, useState } from 'react'

const questions = [
  ['采购全景', '给我采购业务全景，统计供应商、物料、销售订单和采购单数量，以及受延期影响的订单和金额。'],
  ['延期影响', '华兴科技的锂离子电芯MAT-001延期，影响哪些销售订单？对照未受影响的订单，计算销售额和需求。'],
  ['替代选择', '比较华兴科技SUP-001的锂离子电芯MAT-001所有备选供货方案，为什么最便宜的不一定能用？只评估。'],
  ['没有可行方案', '海威电子SUP-004的光学镜头MAT-004延期，有没有能全量准时供货的备选？列出各候选失败原因。'],
  ['预算不足', '比较华兴科技SUP-001的主控芯片MAT-005备选方案，为什么完整替代超出预算？'],
  ['追溯业务关系', '沿O1查客户、物料、供应商、最初采购单、分货批次和计划，给出编号及供应商评分。'],
  ['销售聚合图表', '把全部销售订单按物料汇总，展示金额排名图表、单数、件数和总计。'],
  ['延期影响汇总', '只统计受延期影响的销售订单，按供应商汇总，展示金额图表和总计。'],
  ['采购台账汇总', '将采购单按供应商汇总，展示金额前5名、单数和全量总计。不要混入销售订单。'],
  ['解释风险评分', 'PLAN-DEMO-RISK为什么是高风险？计算分数并解释规则，这是不是AI预测？'],
]

export function SupplierDemoHome({ onStart, onQuestion }: { onStart: () => void; onQuestion: (question: string) => void }) {
  const [summary, setSummary] = useState<{ counts: Record<string, number>; affectedOrderCount: number; affectedSalesAmount: number } | null>(null)
  useEffect(() => { fetch('/api/demo/overview').then(r => r.ok ? r.json() : null).then(setSummary).catch(() => {}) }, [])
  return <div className="flex-1 overflow-y-auto bg-slate-50 text-slate-800">
    <div className="max-w-5xl mx-auto px-8 py-10">
      <p className="text-sm font-medium text-blue-600">OntoPilot · 采购运营演示</p>
      <h1 className="text-3xl font-bold mt-2">从供应商延期，到可核对的处理方案</h1>
      <p className="text-slate-500 mt-3">原项目采购台账与新增销售需求共用一套供应商、物料和业务关系。所有记录均为教学数据。</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-7">
        {([['供应商', 'Supplier'], ['物料', 'Material'], ['销售订单', 'Order'], ['采购单', 'PurchaseOrder']] as const).map(([label, kind]) =>
          <div key={kind} className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="text-sm text-slate-500">{label}</div>
            <div className="text-3xl font-semibold mt-2">{summary ? summary.counts[kind] : '—'}</div>
          </div>)}
      </div>
      <div className="mt-5 rounded-xl bg-amber-50 border border-amber-200 px-5 py-4 text-sm">
        {summary ? `当前有 ${summary.affectedOrderCount} 张销售订单受影响，涉及销售金额 ${summary.affectedSalesAmount.toLocaleString()} 元。` : '正在读取业务概览…'}
        <span className="text-slate-500"> 这是受影响规模，不是已发生损失。</span>
      </div>
      <div className="flex items-center justify-between mt-8 mb-4">
        <h2 className="font-semibold text-lg">选一个业务问题开始展示</h2>
        <button onClick={onStart} className="text-sm text-blue-600 hover:underline">开始对话</button>
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        {questions.map(([label, question], i) => <button key={label} onClick={() => onQuestion(question)}
          className="rounded-xl border border-slate-200 bg-white p-5 text-left hover:border-blue-400 hover:bg-blue-50 transition-colors">
          <div className="text-sm font-semibold"><span className="text-blue-600 mr-2">{String(i+1).padStart(2, '0')}</span>{label}</div>
          <p className="text-sm text-slate-500 mt-2 leading-relaxed">{question}</p>
        </button>)}
      </div>
      <p className="mt-6 text-xs text-slate-500">固定快照：2026-07-01。AI 理解问题和组织工具调用；金额、约束及评分由业务函数计算。查询与评估不会自动提交采购变更。</p>
    </div>
  </div>
}
