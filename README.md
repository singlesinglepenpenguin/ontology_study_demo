# Palantir 本体论与 AI Agent 调研

当前主文档：[Palantir 本体论入门介绍](Palantir本体论_入门介绍.md)。包含基础概念、AI 协作、供应商延期案例的从零建模方法、业务案例和四张本地配图。

上一版 [小白讲稿](Palantir本体论_小白讲稿.md) 保留为历史稿，后续如需演讲版，可根据当前介绍稿重新编排。

- [实践指南](实践指南.md)：GitHub 项目、运行条件、正确命令及验证边界。
- [资料来源](资料来源.md)：官方来源、客户公告与仓库版本记录。
- [配图说明](assets/README.md)：原创示意图与引用图片的来源。
- [本地演示说明](demo/README.md)：无需账号或密钥，体验查询、测算、审批和留痕。
- [OntoPilot 供应商示例](demo/ontopilot_supplier/README.md)：将第 6 节的本体定义、关系与业务函数对应到开源框架；规则、SQLite 集成、真实 DeepSeek 问答及浏览器流程已验证。
- `repos/`：已克隆 Palantir 社区注册库和 Neo4j GraphRAG 示例，保留原许可证。

```bash
python3 demo/demo.py
```

本地演示是规则模拟，已经运行验证；开源 Agent 尚需数据库和模型密钥，Palantir 案例尚需平台环境。具体记录见实践指南。
