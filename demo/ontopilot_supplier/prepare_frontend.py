"""Apply small, reversible UI adaptations; default builds retain upstream accounts."""
from pathlib import Path
import shutil

from run import HERE


def replace_once(path: Path, original: str, replacement: str):
    text = path.read_text()
    if replacement in text:
        return
    if text.count(original) != 1:
        raise RuntimeError(f"上游文件发生变化，请检查后再适配：{path.name}")
    path.write_text(text.replace(original, replacement, 1))


def main():
    root = HERE / "frontend"
    replace_once(
        root / "src/components/LoginPage.tsx",
        "const ACCOUNTS: { username: string; label: string; password: string; desc: string }[] = [",
        "const ACCOUNTS: { username: string; label: string; password: string; desc: string }[] = __SUPPLIER_DEMO__ ? [\n"
        "  { username: 'viewer', label: '查询员', password: 'demo123', desc: '查询订单、关系与供货方案' },\n"
        "  { username: 'buyer', label: '采购员', password: 'demo123', desc: '提交申请和执行获批变更' },\n"
        "  { username: 'approver', label: '审批员', password: 'demo123', desc: '复核并批准供应商变更' },\n"
        "] : [",
    )
    replace_once(
        root / "vite.config.ts", "  plugins: [react()],",
        "  plugins: [react()],\n  define: { __SUPPLIER_DEMO__: JSON.stringify(process.env.ONTOPILOT_SUPPLIER_DEMO === '1') },",
    )
    replace_once(
        root / "src/components/ChatPanel.tsx",
        'placeholder="输入业务问题，例如：查询华南仓所有延迟的货物..."',
        'placeholder={__SUPPLIER_DEMO__ ? "输入业务问题，例如：华兴科技的电芯延期影响哪些订单？" : "输入业务问题，例如：查询华南仓所有延迟的货物..."}',
    )
    replace_once(
        root / "src/App.tsx",
        "user.role === 'admin' ? '管理员' : user.role === 'regional_manager' ? '区域经理' : '调度员'",
        "user.role === 'viewer' ? '只读' : user.role === 'buyer' ? '采购' : user.role === 'approver' ? '审批' : user.role === 'admin' ? '管理员' : user.role === 'regional_manager' ? '区域经理' : '调度员'",
    )
    (root / "src/supplier-demo.d.ts").write_text("declare const __SUPPLIER_DEMO__: boolean;\n")
    shutil.copy2(Path(__file__).parent / "model/SupplierDemoHome.tsx", root / "src/components/SupplierDemoHome.tsx")
    replace_once(root / "src/components/WelcomePage.tsx", "import React from 'react'",
                 "import React from 'react'\nimport { SupplierDemoHome } from './SupplierDemoHome'")
    replace_once(root / "src/components/WelcomePage.tsx", "  onStart: () => void",
                 "  onStart: () => void\n  onDemoQuestion?: (question: string) => void")
    replace_once(root / "src/components/WelcomePage.tsx",
                 "export function WelcomePage({ onStart, onViewChange }: Props) {",
                 "export function WelcomePage({ onStart, onViewChange, onDemoQuestion }: Props) {\n"
                 "  if (__SUPPLIER_DEMO__) return <SupplierDemoHome onStart={onStart} onQuestion={onDemoQuestion || onStart} />")
    replace_once(root / "src/App.tsx", "            onStart={startChat}",
                 "            onStart={startChat}\n            onDemoQuestion={question => { startChat(); void sendMessage(question, false) }}")
    for filename in ("supplierStream.ts", "SupplierActivity.tsx", "SupplierOntologyPanel.tsx", "SupplierDataPanel.tsx", "SessionTitleEditor.tsx", "SupplierRequestStatus.tsx"):
        destination = root / ("src/supplierStream.ts" if filename.endswith(".ts") else f"src/components/{filename}")
        shutil.copy2(Path(__file__).parent / "model" / filename, destination)
    replace_once(root / "src/App.tsx", "import { useSSE } from './hooks/useSSE'",
                 "import { supplierStream } from './supplierStream'\nimport { useSSE } from './hooks/useSSE'")
    replace_once(root / "src/App.tsx", "useSSE(sessionId, handleTraceEvent)",
                 "useSSE(__SUPPLIER_DEMO__ ? null : sessionId, handleTraceEvent)")
    app_path = root / "src/App.tsx"
    app_text = app_path.read_text()
    app_path.write_text(app_text.replace("prev.map((msg, i) => i === prev.length - 1 ? fn(msg) : msg)",
                                          "prev.map(msg => msg.role === 'assistant' && msg.timestamp === assistant.timestamp ? fn(msg) : msg)"))
    branch = (Path(__file__).parent / "model/stream_branch.txt").read_text()
    marker = "      const res = await fetch('/api/chat', {"
    current = app_path.read_text()
    start = current.find("      if (__SUPPLIER_DEMO__) {")
    end = current.find(marker)
    if start >= 0 and end > start:
        app_path.write_text(current[:start] + branch + current[end:])
    else:
        replace_once(app_path, marker, branch + marker)
    replace_once(root / "src/types.ts", "  awaiting_confirmation?: boolean",
                 "  steps?: string[]\n  charts?: import('./components/SupplierActivity').AggregateView[]\n  streaming?: boolean\n  awaiting_confirmation?: boolean")
    replace_once(root / "src/components/ChatPanel.tsx", "import { Markdown } from './Markdown'",
                 "import { Markdown } from './Markdown'\nimport { SupplierActivity } from './SupplierActivity'")
    if "<SupplierActivity steps={msg.steps}" not in (root / "src/components/ChatPanel.tsx").read_text():
        replace_once(root / "src/components/ChatPanel.tsx", '<div className="text-sm text-gray-800 leading-relaxed">',
                     '<SupplierActivity steps={msg.steps} charts={msg.charts} streaming={msg.streaming} />\n                    <div className="text-sm text-gray-800 leading-relaxed">')
    replace_once(root / "src/components/ChatPanel.tsx", "{loading && (", "{loading && !messages.some(m => m.streaming) && (")
    if "toolResults?: Message['toolResults']" not in app_path.read_text():
        replace_once(root / "src/App.tsx", "(m: { role: string; content: string; timestamp: string })", "(m: { role: string; content: string; timestamp: string; steps?: string[]; charts?: Message['charts'] })")
    replace_once(root / "src/App.tsx", "        timestamp: m.timestamp,", "        timestamp: m.timestamp,\n        steps: m.steps, charts: m.charts,")
    replace_once(root / "src/components/Markdown.tsx", '<div key={key} className="overflow-x-auto my-2">',
                 '<div key={`${key}-table`} className="overflow-x-auto my-2">')
    replace_once(root / "src/types.ts", "  steps?: string[]",
                 "  toolResults?: import('./components/SupplierActivity').ToolResult[]\n  steps?: string[]")
    replace_once(root / "src/App.tsx", "charts?: Message['charts']", "charts?: Message['charts']; toolResults?: Message['toolResults']")
    replace_once(root / "src/App.tsx", "steps: m.steps, charts: m.charts,", "steps: m.steps, charts: m.charts, toolResults: m.toolResults,")
    replace_once(root / "src/components/ChatPanel.tsx", "charts={msg.charts} streaming={msg.streaming}", "charts={msg.charts} streaming={msg.streaming} toolResults={msg.toolResults}")
    chat_path = root / "src/components/ChatPanel.tsx"
    chat_text = chat_path.read_text()
    if "toolResults={msg.toolResults}" in chat_text:
        chat_path.write_text(chat_text.replace("                    <SupplierActivity steps={msg.steps} charts={msg.charts} streaming={msg.streaming} />\n", ""))
    replace_once(root / "src/App.tsx", "import { OntologyConfigPanel } from './components/OntologyConfigPanel'",
                 "import { OntologyConfigPanel } from './components/OntologyConfigPanel'\nimport { SupplierOntologyPanel } from './components/SupplierOntologyPanel'\nimport { SupplierDataPanel } from './components/SupplierDataPanel'")
    replace_once(root / "src/App.tsx", "            <OntologyConfigPanel onActivate={setSelectedOntology} />",
                 "            {__SUPPLIER_DEMO__ ? <SupplierOntologyPanel /> : <OntologyConfigPanel onActivate={setSelectedOntology} />}")
    replace_once(root / "src/components/Sidebar.tsx", "'chat' | 'config' | 'ontology' | 'users'", "'chat' | 'config' | 'ontology' | 'users' | 'data'")
    replace_once(root / "src/components/Sidebar.tsx", "        {items.map(item => (",
                 "        {(__SUPPLIER_DEMO__ ? [...items.slice(0, 2), { id: 'data' as ViewType, label: '数据明细', icon: items[1].icon }, ...items.slice(2)] : items).map(item => (")
    replace_once(root / "src/App.tsx", "        {/* Users panel */}",
                 "        {__SUPPLIER_DEMO__ && activeView === 'data' && <div className=\"flex-1 overflow-hidden\"><SupplierDataPanel /></div>}\n\n        {/* Users panel */}")
    replace_once(root / "src/App.tsx", "import { SupplierDataPanel } from './components/SupplierDataPanel'",
                 "import { SupplierDataPanel } from './components/SupplierDataPanel'\nimport { SessionTitleEditor } from './components/SessionTitleEditor'")
    replace_once(root / "src/App.tsx", "                        <button\n                          onClick={(e) => deleteSession(s.id, e)}",
                 "                        {__SUPPLIER_DEMO__ && <SessionTitleEditor id={s.id} title={s.title} onSaved={fetchSessions} />}\n                        <button\n                          onClick={(e) => deleteSession(s.id, e)}")
    replace_once(root / "src/components/ChatPanel.tsx", "import { SupplierActivity } from './SupplierActivity'",
                 "import { SupplierActivity } from './SupplierActivity'\nimport { SupplierRequestStatus } from './SupplierRequestStatus'")
    if "<SupplierRequestStatus loading={loading}" not in chat_path.read_text():
        replace_once(chat_path, "      {/* Messages */}",
                     "      {__SUPPLIER_DEMO__ && <SupplierRequestStatus loading={loading} />}\n      {/* Messages */}")
    replace_once(root / "src/types.ts", "  toolResults?:", "  caseContext?: string\n  toolResults?:")
    replace_once(root / "src/App.tsx", "toolResults?: Message['toolResults']", "toolResults?: Message['toolResults']; caseContext?: string")
    replace_once(root / "src/App.tsx", "toolResults: m.toolResults,", "toolResults: m.toolResults, caseContext: m.caseContext,")
    replace_once(root / "src/components/ChatPanel.tsx", "  const emptyState = messages.length === 0", "  const emptyState = messages.length === 0\n  const caseContext = messages.find(message => message.caseContext)?.caseContext")
    # Remove the old banner on upgrades; keep case metadata for read-only access.
    banner = '      {caseContext && <div className="p-3 bg-amber-50 border-b text-sm text-amber-900">{caseContext} 请新建对话操作当前业务。</div>}\n'
    chat_path.write_text(chat_path.read_text().replace(banner, ""))
    replace_once(root / "src/components/ChatPanel.tsx", "disabled={loading}", "disabled={loading || !!caseContext}")
    replace_once(root / "src/components/ChatPanel.tsx", "disabled={loading || !input.trim()}", "disabled={loading || !!caseContext || !input.trim()}")
    # Upgrade earlier adapter runs that inserted the status line twice.
    lines = chat_path.read_text().splitlines(keepends=True)
    seen_status = False
    cleaned = []
    for line in lines:
        if "<SupplierRequestStatus loading={loading}" in line:
            if seen_status:
                continue
            seen_status = True
        cleaned.append(line)
    chat_path.write_text("".join(cleaned))
    replace_once(chat_path, "__SUPPLIER_DEMO__ && <SupplierRequestStatus", "__SUPPLIER_DEMO__ && !caseContext && <SupplierRequestStatus")
    from prepare_accounts import apply as apply_accounts
    apply_accounts(root, replace_once)
    print("供应商界面适配完成；设置 ONTOPILOT_SUPPLIER_DEMO=1 构建才会启用。")


if __name__ == "__main__":
    main()
