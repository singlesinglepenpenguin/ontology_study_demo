import React, { useEffect, useState } from 'react'

export interface ModelInfo {
  activeOntology: string
  objects: { name: string; description: string; count: number; primaryKey: string;
    properties: Record<string, { description?: string; type?: string }>; links: Record<string, { target: string; foreignKey: string }> }[]
  functions: { name: string; description: string }[]
  actions: { name: string; description: string }[]
}
export function SupplierOntologyPanel() {
  const [model, setModel] = useState<ModelInfo | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { fetch('/api/demo/model').then(async r => { if (!r.ok) throw new Error('读取本体状态失败'); return r.json() }).then(setModel).catch(e => setError(e.message)) }, [])
  return <div className="h-full overflow-auto p-8">
    <h1 className="text-xl font-semibold">采购本体配置</h1>
    {error && <p className="text-red-600 mt-4">{error}</p>}
    {!model && !error && <p className="mt-4">正在读取服务状态…</p>}
    {model && <>
      <div className="mt-4 p-4 rounded-xl border border-green-200 bg-green-50" data-testid="active-ontology">
        <strong className="text-green-800">已自动加载 · {model.activeOntology}</strong>
        <p className="text-sm mt-2 text-green-800">服务启动时已加载采购本体，对话直接使用它。无需点击激活，切换页面也不会失效。</p>
      </div>
      <p className="my-5 text-sm text-gray-500">{model.objects.length} 类对象 · {model.functions.length} 个函数 · {model.actions.length} 个操作。对象定义和关系在此查看，实际记录请打开左侧「数据明细」。</p>
      <h2 className="font-semibold mb-3">对象与关系</h2>
      <div className="grid lg:grid-cols-2 gap-3">{model.objects.map(object => <details key={object.name} className="border rounded-lg p-4 bg-white">
        <summary className="cursor-pointer font-medium">{object.name} <span className="text-xs text-gray-500">{object.count} 条记录</span></summary>
        <p className="text-sm text-gray-500 mt-2">{object.description}</p>
        <p className="text-xs mt-2">唯一编号：{object.primaryKey}</p>
        <dl className="text-xs mt-3 space-y-1">{Object.entries(object.properties).map(([key, property]) => <div key={key}><dt className="inline font-mono">{key}</dt><dd className="inline text-gray-500"> · {property.description || property.type}</dd></div>)}</dl>
        <ul className="text-xs mt-3 text-blue-700">{Object.entries(object.links).map(([key, link]) => <li key={key}>{key} → {link.target}（通过 {link.foreignKey}）</li>)}</ul>
      </details>)}</div>
      {([['业务函数', model.functions], ['业务操作', model.actions]] as const).map(([title, entries]) => <section key={title} className="mt-7">
        <h2 className="font-semibold mb-3">{title}</h2><div className="space-y-2">{entries.map(entry => <div className="bg-white border rounded p-3 text-sm" key={entry.name}><strong>{entry.name}</strong><p className="text-gray-500 mt-1">{entry.description}</p></div>)}</div>
      </section>)}
    </>}
  </div>
}
