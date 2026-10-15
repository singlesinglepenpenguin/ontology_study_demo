import { chromium } from '../../repos/ontopilot/frontend/node_modules/playwright-core/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const output = fileURLToPath(new URL('./results/', import.meta.url))
await mkdir(output, { recursive: true })
const browser = await chromium.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
})
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  page.on('console', msg => { if (msg.type() === 'error' && /same key|unique.*key/i.test(msg.text())) errors.push(msg.text()) })
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /查询员/ }).click()
  await page.locator('input[type=password]').fill('demo123')
  await page.getByRole('button', { name: '进入系统' }).click()
  await page.getByText('48', { exact: true }).waitFor()
  await page.screenshot({ path: output + 'supplier-home.png', fullPage: true })
  const chatResponse = page.waitForResponse(
    r => r.url().endsWith('/api/chat/live') && r.request().method() === 'POST',
    { timeout: 180000 },
  )
  chatResponse.catch(() => {})
  await page.getByRole('button', { name: /02\s*延期影响/ }).click()
  await page.locator('textarea').waitFor()
  await page.getByRole('button', { name: '本体可视化', exact: true }).click()
  await page.getByText('Supplier', { exact: true }).first().waitFor()
  await page.getByTestId('execution-progress').waitFor()
  if (!(await page.locator('textarea').isDisabled())) throw new Error('No progress visible during request')
  await page.screenshot({ path: output + 'supplier-progress.png', fullPage: true })
  const response = await chatResponse
  const frames = (await response.text()).split('\n\n').filter(s => s.startsWith('data: ')).map(s => JSON.parse(s.slice(6)))
  const result = frames.find(e => e.type === 'complete')
  if (frames.filter(e => e.type === 'answer_delta').length < 2) throw new Error('Answer was not streamed')
  if (response.status() !== 200 || !result.response?.includes('O1') || !result.response?.includes('O2')) {
    throw new Error('Browser chat did not return the expected order references; inspect backend status.')
  }
  if (!(result.trace_events || []).some(e => e.name === 'function:assessSupplierDelay' && e.status === 'success')) {
    throw new Error('Browser chat did not call assessSupplierDelay.')
  }
  await page.getByText('O1', { exact: false }).first().waitFor()
  if (errors.length) throw new Error(`Browser runtime errors: ${errors.join('; ')}`)
  await page.screenshot({ path: output + 'supplier-browser.png', fullPage: true })
  const aggregation = page.waitForResponse(r => r.url().endsWith('/api/chat/live') && r.request().method() === 'POST', { timeout: 180000 })
  await page.locator('textarea').fill('只统计受延期影响的销售订单，按供应商汇总，展示金额图表和总计。')
  await page.getByRole('button', { name: '发送', exact: true }).click()
  await page.getByTestId('aggregate-view').waitFor({ timeout: 180000 })
  await page.getByTestId('aggregate-view').getByText(/277,000/).waitFor()
  const aggregateResponse = await aggregation
  const aggregateFrames = (await aggregateResponse.text()).split('\n\n').filter(s => s.startsWith('data: ')).map(s => JSON.parse(s.slice(6)))
  if (!aggregateFrames.some(e => e.type === 'visualization' && e.totals.amount === 277000)) throw new Error('Wrong aggregate')
  await page.getByRole('button', { name: '本体可视化', exact: true }).click()
  await page.getByTestId('aggregate-view').last().scrollIntoViewIfNeeded()
  await page.screenshot({ path: output + 'supplier-aggregate.png', fullPage: true })
  if (errors.length) throw new Error(`Browser runtime errors: ${errors.join('; ')}`)
  await writeFile(output + 'browser-stream.json', JSON.stringify({ status: 'passed', frames, aggregateFrames }, null, 2))
  await writeFile(output + 'browser.json', JSON.stringify({ status: 'passed', ...result }, null, 2))
  console.log('PASS: login, live progress before completion, streamed answer, ontology graph, aggregation chart (277000), real DeepSeek; screenshots saved.')
} finally {
  await browser.close()
}
