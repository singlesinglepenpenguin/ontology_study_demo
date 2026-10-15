"""Apply small, reversible UI adaptations; default builds retain upstream accounts."""
from pathlib import Path
import shutil

from run import UPSTREAM


def replace_once(path: Path, original: str, replacement: str):
    text = path.read_text()
    if replacement in text:
        return
    if text.count(original) != 1:
        raise RuntimeError(f"上游文件发生变化，请检查后再适配：{path.name}")
    path.write_text(text.replace(original, replacement, 1))


def main():
    root = UPSTREAM / "frontend"
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
    print("供应商界面适配完成；设置 ONTOPILOT_SUPPLIER_DEMO=1 构建才会启用。")


if __name__ == "__main__":
    main()
