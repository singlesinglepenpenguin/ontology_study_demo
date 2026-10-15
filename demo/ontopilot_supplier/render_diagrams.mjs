import { chromium } from '../../repos/ontopilot/frontend/node_modules/playwright-core/index.mjs'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true })
try {
  for (const [name, height] of [['01-ontology-model', 650], ['02-ai-workflow', 635]]) {
    const source = fileURLToPath(new URL(`../../assets/${name}.svg`, import.meta.url))
    const page = await browser.newPage({ viewport: { width: 1200, height } })
    await page.setContent(`<style>body{margin:0}</style>${await readFile(source, 'utf8')}`)
    await page.screenshot({ path: fileURLToPath(new URL(`../../assets/${name}.png`, import.meta.url)) })
    await page.close()
  }
} finally { await browser.close() }
