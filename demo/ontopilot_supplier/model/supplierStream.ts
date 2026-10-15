export async function supplierStream(body: unknown, onEvent: (event: any) => void) {
  const response = await fetch('/api/chat/live', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (!response.ok || !response.body) throw new Error(`请求失败 (${response.status})`)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = '', completed = false
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let end: number
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        const frame = buffer.slice(0, end)
        buffer = buffer.slice(end + 2)
        if (!frame.startsWith('data: ')) continue
        const event = JSON.parse(frame.slice(6))
        if (event.type === 'error') throw new Error(event.message)
        if (event.type === 'complete') completed = true
        onEvent(event)
      }
      if (done) break
    }
    if (!completed) throw new Error('连接中断，回答未完成；涉及写操作时请先查询申请状态。')
  } finally { await reader.cancel(); reader.releaseLock() }
}
