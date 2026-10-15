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
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /查询员/ }).click()
  await page.locator('input[type=password]').fill('demo123')
  await page.getByRole('button', { name: '进入系统' }).click()
  await page.getByText('48', { exact: true }).waitFor()
  await page.screenshot({ path: output + 'supplier-home.png', fullPage: true })
  const chatResponse = page.waitForResponse(
    r => r.url().endsWith('/api/chat') && r.request().method() === 'POST',
    { timeout: 180000 },
  )
  chatResponse.catch(() => {})
  await page.getByRole('button', { name: /02\s*延期影响/ }).click()
  await page.locator('textarea').waitFor()
  await page.getByRole('button', { name: '本体可视化', exact: true }).click()
  await page.getByText('Supplier', { exact: true }).first().waitFor()
  const response = await chatResponse
  const result = await response.json()
  if (response.status() !== 200 || !result.response?.includes('O1') || !result.response?.includes('O2')) {
    throw new Error('Browser chat did not return the expected order references; inspect backend status.')
  }
  if (!(result.trace_events || []).some(e => e.name === 'function:assessSupplierDelay' && e.status === 'success')) {
    throw new Error('Browser chat did not call assessSupplierDelay.')
  }
  await page.getByText('O1', { exact: false }).first().waitFor()
  if (errors.length) throw new Error(`Browser runtime errors: ${errors.join('; ')}`)
  await page.screenshot({ path: output + 'supplier-browser.png', fullPage: true })
  await writeFile(output + 'browser.json', JSON.stringify({ status: 'passed', ...result }, null, 2))
  console.log('PASS: login, ontology graph, real DeepSeek chat, function trace; screenshot saved.')
} finally {
  await browser.close()
}
