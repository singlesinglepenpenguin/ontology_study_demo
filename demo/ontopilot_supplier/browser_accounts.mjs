import { chromium } from '../../repos/ontopilot/frontend/node_modules/playwright-core/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
const base = 'http://127.0.0.1:8001'
const output = fileURLToPath(new URL('./results/', import.meta.url))
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } })
  const errors = []; const turns = []
  page.on('pageerror', error => errors.push(error.message))
  async function login(label) {
    await page.getByRole('button', { name: new RegExp(label) }).click()
    await page.locator('input[type=password]').fill('demo123')
    await page.getByRole('button', { name: '进入系统' }).click()
    await page.getByRole('button', { name: '开始对话', exact: true }).waitFor()
  }
  async function turn(question, confirm = false) {
    const received = page.waitForResponse(r => r.url().endsWith('/api/chat/live') && r.request().method() === 'POST', { timeout: 180000 })
    if (confirm) await page.getByRole('button', { name: '确认执行', exact: true }).last().click()
    else { await page.locator('textarea').fill(question); await page.getByRole('button', { name: '发送', exact: true }).click() }
    const response = await received
    if (response.status() !== 200) throw new Error(`Chat failed: ${response.status()} ${await response.text()}`)
    const frames = (await response.text()).split('\n\n').filter(s => s.startsWith('data: ')).map(s => JSON.parse(s.slice(6)))
    const final = frames.find(e => e.type === 'complete')
    if (!final) throw new Error('No complete event')
    turns.push({ question, frames })
    await page.waitForFunction(() => !document.querySelector('textarea')?.disabled)
    return final
  }
  async function logout() {
    await page.getByRole('button', { name: '退出', exact: true }).click()
    await page.getByRole('button', { name: '进入系统' }).waitFor()
  }
  await page.goto(base, { waitUntil: 'networkidle' })
  await login('查询员')
  await page.getByRole('button', { name: '开始对话', exact: true }).click()
  const viewer = await turn('查询员独有历史标记：请查询 O1 的销售额。')
  await logout()
  await login('采购员')
  const listed = await (await page.request.get(base + '/api/sessions')).json()
  if (listed.sessions.some(s => s.id === viewer.session_id)) throw new Error('Viewer history leaked in buyer list')
  for (const method of ['get', 'delete']) {
    const res = await page.request[method](base + '/api/sessions/' + viewer.session_id)
    if (res.status() !== 403) throw new Error('Cross-account access allowed')
  }
  const rejected = await page.request.post(base + '/api/chat/live', { data: { session_id: viewer.session_id, message: '推进' } })
  if (rejected.status() !== 403) throw new Error('Cross-account continuation allowed')
  await page.getByRole('button', { name: '开始对话', exact: true }).click()
  if (await page.getByText(/查询员独有历史标记/).count()) throw new Error('Viewer message remained after switch')
  let final = await turn('采购员提交验证：请按 submitSupplierChange 提交原供应商SUP-001、电芯MAT-001的OPT-MAT-001-FAST方案，先查询评估并预览，等待我点击确认。不要审批或执行采购变更。')
  if (!final.awaiting_confirmation) throw new Error('Buyer did not get an authorized preview')
  final = await turn('确认提交', true)
  let requests = (await (await page.request.get(base + '/api/demo/data?object_type=ChangeRequest')).json()).rows
  if (requests.length !== 1 || requests[0].createdBy !== 'buyer-demo' || requests[0].status !== 'pending') throw new Error('Buyer submission failed')
  const rid = requests[0].requestId
  await page.screenshot({ path: output + 'buyer-submit.png', fullPage: true })
  const buyerSid = final.session_id
  await turn(`申请 ${rid} 还在待审批阶段。请调用 preview_action 预览 executeSupplierChange，验证未审批时会被拦截，不要执行。`)
  await logout()
  await login('审批员')
  const approverHistory = await (await page.request.get(base + '/api/sessions')).json()
  if (approverHistory.sessions.length) throw new Error('Approver sees another account history')
  await page.getByRole('button', { name: '开始对话', exact: true }).click()
  final = await turn(`请查询并审批共享业务申请 ${rid}，使用 approveSupplierChange，先预览等待我点击确认，不执行采购变更。`)
  if (!final.awaiting_confirmation) throw new Error('Approver preview missing')
  const approvedTurn = await turn('确认审批', true)
  const approverSession = (await (await page.request.get(base + '/api/sessions/' + approvedTurn.session_id)).json()).session
  requests = (await (await page.request.get(base + '/api/demo/data?object_type=ChangeRequest')).json()).rows
  if (requests[0].status !== 'approved' || requests[0].approvedBy !== 'approver-demo') throw new Error('Approval failed')
  await logout()
  await login('采购员')
  const buyerHistory = await (await page.request.get(base + '/api/sessions')).json()
  if (!buyerHistory.sessions.some(s => s.id === buyerSid) || buyerHistory.sessions.some(s => s.id === viewer.session_id)) throw new Error('Buyer history ownership wrong after relogin')
  await page.getByRole('button', { name: '开始对话', exact: true }).click()
  await page.getByRole('button', { name: /采购员提交验证/ }).first().click()
  const refreshed = await turn(`查询申请 ${rid} 的最新审批状态，是否已经审批好了？不要沿用历史结果，先调用 getChangeRequest。`)
  if (!/approved|已批准|审批通过/.test(refreshed.response)) throw new Error('Buyer reused stale pending after approval')
  final = await turn(`请查询已批准申请 ${rid}，按 executeSupplierChange 执行，先给我预览，等待我点击确认。`)
  if (!final.awaiting_confirmation) throw new Error('Execution preview missing')
  await turn('确认执行采购变更', true)
  requests = (await (await page.request.get(base + '/api/demo/data?object_type=ChangeRequest')).json()).rows
  if (requests[0].status !== 'executed') throw new Error('Execution failed')
  const o1 = await (await page.request.get(base + '/api/demo/data?' + new URLSearchParams({ filters: JSON.stringify({ orderId: 'O1' }) }))).json()
  if (o1.rows[0].supplierId !== 'SUP-006') throw new Error('Order not updated')
  const budget = await (await page.request.get(base + '/api/demo/data?object_type=Policy')).json()
  if (budget.rows[0].extraBudget !== 10000) throw new Error('Budget not updated')
  if (errors.length) throw new Error(errors.join('; '))
  const buyerSession = (await (await page.request.get(base + '/api/sessions/' + buyerSid)).json()).session
  await writeFile(output + 'snapshot-dialogues.json', JSON.stringify({ context: '独立初始教学快照的真实 DeepSeek 对话及工具结果；业务写入只发生于临时数据库，不代表当前采购台账状态。', sessions: [buyerSession, approverSession] }, null, 2))
  await writeFile(output + 'accounts-browser.json', JSON.stringify({ status: 'passed', isolatedDatabase: true, viewerSid: viewer.session_id, buyerSid, request: requests[0], turns }, null, 2))
  console.log('PASS: private history, cross-account GET/DELETE/POST denied, role switching, real buyer submit -> approver approve -> buyer execute; disposable SQLite only.')
} finally { await browser.close() }
