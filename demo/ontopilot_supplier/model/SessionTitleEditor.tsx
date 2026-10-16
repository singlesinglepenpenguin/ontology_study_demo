import React, { useState } from 'react'

export function SessionTitleEditor({ id, title, onSaved }: { id: string; title: string; onSaved: () => void }) {
  const [editing, setEditing] = useState(false), [value, setValue] = useState(title)
  const [error, setError] = useState(''), [saving, setSaving] = useState(false)
  async function save(event: React.FormEvent) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      const response = await fetch('/api/sessions/' + id, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: value.trim() }) })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || '保存失败')
      setEditing(false); onSaved()
    } catch (e) { setError(e instanceof Error ? e.message : '保存失败') } finally { setSaving(false) }
  }
  return <>
    <button onClick={() => { setValue(title); setEditing(true) }} className="absolute right-7 top-2 p-1 text-gray-400 hover:text-blue-600 bg-white/80 rounded" title="编辑会话标题" aria-label={`编辑标题：${title}`}>✎</button>
    {editing && <div className="fixed inset-0 z-50 bg-black/20 flex items-center justify-center" role="dialog" aria-label="编辑会话标题">
      <form onSubmit={save} className="bg-white border rounded-xl p-5 shadow-xl w-96 space-y-3">
        <h2 className="font-semibold">编辑会话标题</h2><input autoFocus aria-label="会话标题" maxLength={100} value={value} onChange={e => setValue(e.target.value)} className="border rounded p-2 w-full text-sm" />
        {error && <p className="text-red-600 text-sm">{error}</p>}<div className="flex justify-end gap-3 text-sm"><button type="button" disabled={saving} onClick={() => setEditing(false)}>取消</button><button disabled={saving || !value.trim()} className="bg-blue-600 text-white rounded px-3 py-1.5">{saving ? '保存中…' : '保存'}</button></div>
      </form>
    </div>}
  </>
}
