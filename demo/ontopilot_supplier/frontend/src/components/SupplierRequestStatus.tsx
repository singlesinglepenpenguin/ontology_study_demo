import React, { useEffect, useState } from 'react'
interface Change { requestId: string; status: string; supplierId: string; materialId: string; approvedBy?: string }
export function SupplierRequestStatus({ loading }: { loading: boolean }) {
  const [requests, setRequests] = useState<Change[]>([]), [error, setError] = useState(''), [revision, setRevision] = useState(0)
  const [readAt, setReadAt] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    const refresh = async () => {
      try {
        const response = await fetch('/api/demo/data?object_type=ChangeRequest&limit=200', { signal: controller.signal })
        if (!response.ok) throw new Error('申请状态读取失败，请重新登录或刷新')
        const body = await response.json(); setRequests(body.rows); setReadAt(body.readAt); setError('')
      } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : '读取失败') }
    }
    void refresh(); const timer = window.setInterval(refresh, 10000)
    window.addEventListener('focus', refresh)
    return () => { controller.abort(); clearInterval(timer); window.removeEventListener('focus', refresh) }
  }, [loading, revision])
  const labels: Record<string, string> = { pending: '待审批', approved: '已批准，待执行', executed: '已执行' }
  return <details className="border-b bg-blue-50 px-4 py-2 text-xs" data-testid="request-status">
    <summary className="cursor-pointer text-blue-800">实时申请状态 · {error || `${requests.length} 条申请`} <span className="text-gray-500 ml-2">历史回复保留当时结果；当前状态以此处读取为准</span></summary>
    <div className="mt-2 flex items-center gap-3"><button className="border rounded bg-white px-2 py-1" onClick={() => setRevision(n => n + 1)}>刷新申请状态</button><span className="text-gray-500">{readAt && `读取于 ${new Date(readAt).toLocaleTimeString('zh-CN')}`} · 每 10 秒更新</span></div>
    <div className="mt-2 max-h-32 overflow-auto space-y-1">{requests.map(request => <div key={request.requestId} className="flex flex-wrap gap-3"><strong>{request.requestId}</strong><span>{labels[request.status] || request.status}（{request.status}）</span><span>{request.supplierId} / {request.materialId}</span>{request.approvedBy && <span>审批人 {request.approvedBy}</span>}</div>)}{!requests.length && !error && <p>当前没有变更申请</p>}</div>
  </details>
}
