# Palantir 本体论与 AI Agent 调研

当前主文档：[Palantir 本体论入门介绍](Palantir本体论_入门介绍.md)。以合并后的 OntoPilot 采购项目贯穿全部案例，包含本体构建、AI 实际分工、可点击的演示问题和四张本地配图。

历史版 [小白讲稿](Palantir本体论_小白讲稿.md) 保留为历史稿，后续如需演讲版，可根据当前介绍稿重新编排。

- [实践指南](实践指南.md)：GitHub 项目、运行条件、正确命令及验证边界。
- [资料来源](资料来源.md)：官方来源、客户公告与仓库版本记录。
- [配图说明](assets/README.md)：原创示意图与引用图片的来源。
- [本地演示说明](demo/README.md)：历史零依赖规则模拟；当前主案例使用下方 OntoPilot 项目。
- [OntoPilot 供应商示例](demo/ontopilot_supplier/README.md)：8 家供应商、48 张销售订单、18 张采购单与 36 个候选报价；已通过 15 项测试、7 组真实对话及浏览器验证。
- `repos/`：已克隆 Palantir 社区注册库和 Neo4j GraphRAG 示例，保留原许可证。

```bash
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py serve
```

访问 http://127.0.0.1:8000，查询员账号 viewer，教学密码 demo123。本机模型与环境已配置；新环境按 Demo 说明安装。旧仓库和规则脚本保留作历史参考。
