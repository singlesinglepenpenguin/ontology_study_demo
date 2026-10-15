# OntoPilot：供应商延期与订单处理

这是在 [jingw2/ontopilot](https://github.com/jingw2/ontopilot) 上添加的原创教学场景，不是 Palantir 产品实现，也不是官方 Onyx 原例。上游代码保存在 `repos/ontopilot/`，当前版本为 `dc9ac375b979c7ea4fa95d209194f55b10f909f9`，MIT 许可证见上游仓库。本目录通过导入上游库进行扩展，没有修改上游 Python 源码。

## 当前验证状态

| 项目 | 状态 |
|---|---|
| 克隆上游项目 | 已完成，固定版本见上 |
| React 前端安装与构建 | `npm install`、`npm run build` 成功 |
| 本例 YAML 语法、Python 语法 | 检查通过 |
| 独立业务规则 | 9 项测试通过，不调用 LLM，不依赖第三方库 |
| OntoPilot SQLite Runtime 接入 | `run.py check` 和 3 项集成测试通过，包含持久化、审计和回滚 |
| DeepSeek Agent 实际问答 | 3 组真实问答通过，已检查实际函数调用轨迹 |
| 原项目 API | 未修改 Python 源码；通过原 FastAPI 应用的启动、登录、会话和种子数据查询验证 |
| 供应商 Demo 浏览器验证 | Chrome 中通过登录、本体图、真实问答及工具轨迹检查 |

此前安装受会话权限限制；本轮设置代理并获准在沙箱外执行后，已成功安装。采用项目 `uv.lock` 的固定版本，避免最新版依赖反复解析。验证摘录见 [问答验证摘录](问答验证摘录.md)，完整范围见 [验证记录](验证记录.md)。

## 本体与数据在哪里

| 文件 | 对应构建步骤 |
|---|---|
| `config/ontology_schema.yaml` | 定义 7 种对象、9 条关系、4 个函数、3 个操作 |
| `config/seed_data.yaml` | 用虚构对象填充模型；包括 S1、O1、O2 及对照订单 O3 |
| `config/permissions.yaml` | 查询员、采购员、审批员的工具权限 |
| `domain.py` | 确定性计算、预算检查、申请、审批和执行规则 |
| `runtime.py` | 接入上游 SchemaRegistry、ObjectStore、FunctionRegistry、ActionExecutor 和审计轨迹 |
| `run.py` | 配置模型、执行 Runtime 检查、单次 Agent 问答、启动服务 |
| `server.py` | 复用上游聊天和会话 API，提供本例配置及原 React 界面 |
| `test_domain.py` / `test_runtime.py` | 独立规则测试 / 真正使用上游 SQLite Runtime 的集成测试 |
| `smoke_live.py` | 调用真实模型，检查回答及实际工具轨迹 |

例如，一条 Order → Customer 关系由以下定义建立；种子数据中的 O1 携带 `customerId: C1`，运行时据此找到实际客户对象。

```yaml
links:
  customer: {target: Customer, foreign_key: customerId}
```

上游 ObjectStore 主要提供沿外键到目标主键的查询。本例将一对多查询表达为按外键过滤，例如查询 `Order`、`supplierId: S1`；ChangeRequest 的 `orderIds` 则通过列表值连接相关订单。Agent 还可调用 `traceOrderRelations` 实际遍历 O1 的客户、商品及供应商关系。

## 安装与启动

以下命令从项目根目录执行。需要 Python 3.11+、Node.js 18+；当前环境的 Python 和前端依赖均已装好。重新安装时使用从上游锁文件导出的固定版本。

```bash
git clone --depth 1 https://github.com/jingw2/ontopilot.git repos/ontopilot
python3 -m venv repos/ontopilot/.venv
export all_proxy=127.0.0.1:7897
repos/ontopilot/.venv/bin/python -m pip install -r demo/ontopilot_supplier/requirements.lock.txt -e ./repos/ontopilot
```

仓库已存在时跳过 clone。上述安装命令会安装当前工作区的上游源码和锁定的开发依赖；上游 dev 使用 dependency-groups 声明，不能靠 `.[dev]` 安装。这里的代理地址是本机配置，其他机器应替换或省略；Python 启动器会为 httpx 自动补全代理 URL 协议。现有本地凭据位于本目录 `.env`，文件权限为 0600，已被根目录 `.gitignore` 排除。新环境可参考 [.env.example](.env.example)。模型配置只存环境变量名，API 地址为 `https://api.deepseek.com`。

按用户要求配置 `deepseek-v4-flash`；DeepSeek 当前官方文档将它作为兼容名称，实际请求由其最新 Flash 服务承接。可通过 `.env` 中的 `DEEPSEEK_MODEL` 调整。上游 `ChatOpenAI` 适配用于工具调用，本例显式关闭 thinking 模式以避免上游对话循环丢失 reasoning_content。[DeepSeek 模型说明](https://api-docs.deepseek.com/quick_start/pricing/)、[工具调用说明](https://api-docs.deepseek.com/guides/tool_calls/)

先验证运行时，随后验证真实问答：

```bash
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py check
repos/ontopilot/.venv/bin/python -m unittest discover -s demo/ontopilot_supplier -p test_runtime.py -v
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/smoke_live.py
```

`check` 和集成测试使用临时 SQLite，不改演示数据。`smoke_live.py` 会产生实际 API 调用费用，用查询员角色执行 3 个问题，不修改业务对象，成功后保存 `results/live.json`。它不仅检查有文字回答，也检查 Agent 是否实际调用了指定函数。

启动原前端配合本例后端：

```bash
python3 demo/ontopilot_supplier/prepare_frontend.py
npm --prefix repos/ontopilot/frontend install
ONTOPILOT_SUPPLIER_DEMO=1 npm --prefix repos/ontopilot/frontend run build
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py serve
```

服务仅绑定本机，浏览器访问 `http://127.0.0.1:8000`。教学账号为 `viewer`（查询）、`buyer`（提交和执行）、`approver`（审批），密码均为 `demo123`。可查看本体结构、聊天与工具轨迹。这是原界面的供应商教学入口；模型设置、用户管理和任意本体上传功能未接入本例。配置更改通过本目录文件进行。

`prepare_frontend.py` 只适配本地前端账号、角色名称和输入提示，默认构建仍保留上游账号。上游 Python 源码不变；这些前端改动由适配脚本复现。

原始项目的 `main.py` 当前只是欢迎语，不能按 README 的该命令启动 API。已通过 `verify_upstream.py` 验证原 `api.main:app` 的完整启动生命周期和原生接口；如需独立启动原 API，可在上游目录加载模型环境变量后执行 `.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8001`。当前演示服务使用 8000 端口。

## 可以问什么

```bash
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py chat '供应商S1延期影响哪些订单？调用函数列出金额和需求数量。'
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py chat '沿O1的关系查出客户、商品和供应商，给出编号。'
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py chat 'OPT-S2-P1能否替代S1？预算只有1000元时呢？只做评估。'
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py chat '为什么更便宜的OPT-S3-P1不能覆盖全部需求？'
```

以下前三项已由真实模型回答和工具轨迹验证，摘录见 [问答验证摘录](问答验证摘录.md)；其余备选方案的失败条件由独立规则测试覆盖：

- O1、O2 缓冲 3 天、5 天，被 7 天延期影响；合计销售金额 100,000 元、需求 100 件。
- O3 缓冲 10 天，本次不受影响，不应计入上述汇总。
- OPT-S2-P1 可供 100 件，每件多 20 元，增量成本 2,000 元；默认预算 3,000 元时可行。
- 假设预算 1,000 元则不满足条件；该测算不会改变真正的策略预算。
- OPT-S3-P1 只有 50 件，不能覆盖全部 100 件；OPT-LATE 交付不及时；OPT-WRONG 商品不匹配。

## 操作闭环与限制

采购员提交申请，另一位审批员批准，再由采购员确认执行。执行前重新检查订单、供货选项及预算指纹；数据变化则要求重新提交审批。执行时将受影响订单改为 S2，扣减选项数量和预算，保存申请与审计。SQLite 写入放在同一事务中，集成测试已验证正常闭环、持久化和注入失败后的回滚。真实模型和浏览器验证聚焦查询与评估，未将其描述为已验证完整的自主审批过程。

这里实现的是教学采购规则。接口沿用上游以请求参数传递角色和用户的方式，确认机制也不能作为经过认证的人类审批凭证；不用于真实采购系统或生产权限隔离。业务规则测试通过不代表身份认证、并发会话和 LLM 自主操作安全已经验证。

服务重启不会重新覆盖已存在的业务对象。重置演示数据需明确执行：

```bash
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py reset
```

重置只用于本例数据库，保留对话和审计；重置后应开启新对话，避免沿用旧申请编号。
