import { chromium } from '../../repos/ontopilot/frontend/node_modules/playwright-core/index.mjs'
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1450, height: 1000 } })
  const errors = []; page.on('pageerror', error => errors.push(error.message))
  async function login(account) {
    await page.getByRole('button', { name: new RegExp(account) }).click()
    await page.locator('input[type=password]').fill('demo123')
    await page.getByRole('button', { name: '进入系统' }).click()
    await page.getByRole('button', { name: '开始对话', exact: true }).click()
  }
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' })
  await login('查询员')
  const original = '文档01·电芯影响与替代（7万/2万）', revised = '验证标题编辑·电芯影响与替代'
  async function rename(from, to) {
    await page.getByRole('button', { name: '编辑标题：' + from, exact: true }).click()
    await page.getByRole('textbox', { name: '会话标题' }).fill(to)
    await page.getByRole('button', { name: '保存', exact: true }).click()
    await page.getByRole('button', { name: '编辑标题：' + to, exact: true }).waitFor()
  }
  await rename(original, revised)
  const sessions = (await (await page.request.get('http://127.0.0.1:8000/api/sessions')).json()).sessions
  if (!sessions.some(session => session.title === revised)) throw new Error('Rename not persisted')
  await rename(revised, original)
  await page.getByTestId('request-status').locator('summary').click()
  await page.getByTestId('request-status').getByText(/已批准，待执行/).waitFor()
  await page.screenshot({ path: 'demo/ontopilot_supplier/results/named-history.png', fullPage: true })
  // Hold a response while navigating. These requests are browser mocks only;
  // no test message or business change is persisted in the live database.
  async function checkNavigation(navigate, expectedSid) {
    console.log('Checking navigation', expectedSid || 'new conversation')
    let release, arrived, probeBody
    const gate = new Promise(resolve => { release = resolve })
    const started = new Promise(resolve => { arrived = resolve })
    let calls = 0
    await page.route('**/api/chat/live', async route => {
      const body = route.request().postDataJSON()
      const first = ++calls === 1
      if (first) { arrived(); await gate } else probeBody = body
      const sid = first ? 'stale-navigation-response' : body.session_id || 'browser-only-response'
      const frames = [{ type: 'session', session_id: sid }, { type: 'complete', session_id: sid, response: '导航验证', awaiting_confirmation: first, pending_action: null, trace_events: [] }]
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body: frames.map(frame => 'data: ' + JSON.stringify(frame) + '\n\n').join('') }).catch(() => {})
    })
    await page.locator('textarea').fill('浏览器临时导航测试')
    await page.getByRole('button', { name: '发送', exact: true }).click()
    await Promise.race([started, new Promise((_, reject) => setTimeout(() => reject(new Error('Chat interception did not start')), 10000))])
    console.log('Delayed response intercepted')
    await navigate()
    console.log('Navigation completed')
    release()
    await page.waitForFunction(() => !document.querySelector('textarea')?.disabled)
    await page.locator('textarea').fill('验证当前会话编号')
    await page.getByRole('button', { name: '发送', exact: true }).click()
    await page.waitForFunction(() => !document.querySelector('textarea')?.disabled)
    if (probeBody?.session_id !== expectedSid) throw new Error('Stale stream overwrote the selected conversation')
    await page.unroute('**/api/chat/live')
  }
  const docSession = sessions.find(session => session.id === '7943a64a-f959-494e-8f67-2ca060a5146f')
  if (!docSession) throw new Error('Document example missing')
  await checkNavigation(async () => {
    await page.getByRole('button', { name: /文档01·电芯影响与替代/ }).filter({ hasNotText: '✎' }).first().click()
    await page.getByText(/O3/).first().waitFor()
  }, docSession.id)
  await checkNavigation(async () => { await page.getByRole('button', { name: '+ 新对话', exact: true }).click() }, null)
  await page.getByRole('button', { name: '退出', exact: true }).click()
  await login('采购员')
  await page.getByRole('button', { name: /快照操作01/ }).filter({ hasNotText: '✎' }).first().click()
  await page.waitForFunction(() => document.querySelector('textarea')?.disabled)
  if (await page.getByText(/独立初始教学快照|请新建对话操作当前业务/).count()) throw new Error('Removed snapshot banner is still visible')
  if (!(await page.locator('textarea').isDisabled())) throw new Error('Snapshot case can be executed against live data')
  if (errors.length) throw new Error(errors.join('; '))
  console.log('PASS: title persistence, live approval status, stream cancellation on history/new-chat navigation, removed banner and read-only archives.')
} finally { await browser.close() }
