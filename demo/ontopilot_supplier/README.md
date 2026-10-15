# OntoPilot 采购运营 Demo

这是基于 [jingw2/ontopilot](https://github.com/jingw2/ontopilot) 的合并采购教学项目，保留上游版本 `dc9ac375b979c7ea4fa95d209194f55b10f909f9` 的 34 条原采购记录及原字段，并统一此前的供应商延期模型。上游和新增记录均为教学数据，不是企业真实数据，也不是 Palantir 官方实现。

## 数据与业务情境

当前初始数据共 170 条，11 种对象：8 家供应商、6 种物料、12 个客户、48 张销售订单、18 张采购单、10 个分货计划、21 个批次、10 条评分、36 个供货选项、1 条预算策略；变更申请初始为空，运行时产生。

统一使用 SUP-xxx、MAT-xxx 编号。原小例子 S1/P1 对应 SUP-001/MAT-001；旧两套编号不再作为两份对象重复存储。来源、映射、mock 字段与数据摘要见 [数据清单](dataset_manifest.json)。Supplier.delayDays、Material.reservedStock 是给上游记录补充的教学假设，其余原字段保持。

| 情境 | 查询入口 | 初始结果 |
|---|---|---|
| 全局概览 | getProcurementOverview | 8 张销售订单受影响，涉及销售额 277,000 元 |
| 电芯可替代 | SUP-001 / MAT-001 | O1、O2，1,000 件、70,000 元；FAST 选项增量成本 20,000 元，预算 30,000 元 |
| 显示屏可替代 | SUP-002 / MAT-002 | 400 件，首个可行选项增量成本 4,800 元 |
| 镜头无可行候选 | SUP-004 / MAT-004 | 需 300 件，候选有交期、数量或状态问题 |
| 芯片预算不足 | SUP-001 / MAT-005 | 需 200 件；全量准时供货最低增量成本 32,000 元，高于预算 |
| 单一来源风险 | PLAN-DEMO-RISK | 上游规则给出 85 分，非 AI 预测概率 |
| 关系追溯 | O1 | 客户→销售需求→物料/供应商→最初采购单→批次→计划，并查询历史评分 |

同一供应商可以供应不同物料。替代报价只覆盖同一 sourceSupplierId + materialId 下的受影响订单；不能把多种物料的总件数用于一个报价。已完成订单不参与延期评估。风险物料的当前库存已全部预留，不做库存分摊或生产排程。

## 哪些文件负责什么

| 文件 | 内容 |
|---|---|
| model/supplier_extension.yaml | 延期、销售需求和供货变更的源定义 |
| build_dataset.py | 合并上游模型、保留原记录、确定性生成 mock 并校验外键 |
| config/ontology_schema.yaml | 生成后的实际模型，包含 8 个函数、3 个操作 |
| config/seed_data.yaml | 实际教学数据；dataOrigin 标明来源 |
| config/permissions.yaml | 查询员、采购员、审批员的工具权限 |
| domain.py / runtime.py | 规则计算、事务、审批及原 OntoPilot Runtime 接入 |
| model/SupplierDemoHome.tsx / prepare_frontend.py | 数据概览和可点击问题；可复现的前端适配 |
| run.py / server.py | 本地模型配置、CLI 与浏览器入口 |
| streaming.py / model/supplierStream.ts | 单条 POST SSE 实时返回执行状态、工具轨迹、回答增量及聚合展示数据 |
| smoke_live.py / smoke_stream.py / browser_smoke.mjs | 真实模型和 Chrome 验证 |

YAML 只声明能力，业务函数仍需 Python 实现。生成、导入、关联、金额和风险评分都不调用 LLM；DeepSeek 在 Agent 中理解问题、组织工具调用并解释结果。没有自动建模、文档 RAG、机器学习预测或自动训练功能。更完整的 AI 分工见主文档第 4 节。

## 安装与运行

从项目根目录执行。当前机器的依赖已装好，原仓库已存在，可直接使用启动命令。

```bash
git clone --depth 1 https://github.com/jingw2/ontopilot.git repos/ontopilot
python3 -m venv repos/ontopilot/.venv
export all_proxy=127.0.0.1:7897
repos/ontopilot/.venv/bin/python -m pip install -r demo/ontopilot_supplier/requirements.lock.txt -e ./repos/ontopilot
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/build_dataset.py
python3 demo/ontopilot_supplier/prepare_frontend.py
npm --prefix repos/ontopilot/frontend install
ONTOPILOT_SUPPLIER_DEMO=1 npm --prefix repos/ontopilot/frontend run build
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py serve
```

仓库已存在时跳过 clone。代理地址按自己的机器配置；启动器会为 httpx 补全协议。上游测试依赖使用 dependency-groups，不能靠 .[dev] 安装，故使用从其 uv.lock 导出的固定版本。

凭据放在本目录被 Git 忽略的 `.env`，参考 [.env.example](.env.example)。使用用户要求的 `deepseek-v4-flash` 请求名；实际服务版本由 DeepSeek 决定，本例关闭 thinking 模式以兼容上游工具调用循环。密钥不放入 YAML 或版本管理。

浏览器访问 **http://127.0.0.1:8000**，教学账号 viewer、buyer、approver，密码均为 `demo123`。首页显示实际统计并提供 10 个可点击问题；进入对话后可打开本体图。模型配置、用户管理及任意本体上传并未接入这个固定场景入口。

新版业务、审计和会话使用 `.procurement-v2.db`，旧 `.ontopilot.db` 保留，不自动覆盖旧演示记录。重新生成 YAML 不会覆盖正在运行的 SQLite；若明确要恢复初始教学数据，执行：

```bash
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py reset
```

重置会保留该版本对话和审计，重置后应开启新对话。

## 验证

```bash
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py check
repos/ontopilot/.venv/bin/python -W ignore::ResourceWarning -m unittest discover -s demo/ontopilot_supplier -p 'test_*.py' -v
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/smoke_live.py
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/smoke_stream.py
node demo/ontopilot_supplier/browser_smoke.mjs
```

19 项程序测试通过，包括原记录保留、跨物料隔离、权限和预算、审批、持久化与回滚；7 组真实 DeepSeek 对话通过，检查实际函数调用；新增 6 组真实流式问答通过，覆盖聚合、多轮筛选、采购 Top N 和空结果；Chrome 中已验证首页统计、登录、本体图、回答完成前的实时进度及聚合图表。调用真实模型会产生 API 费用。记录见 [问答摘录](问答验证摘录.md) 、[流式问答摘录](流式问答验证.md) 与 [验证记录](验证记录.md)。

原项目 API 的启动、登录、会话和默认数据查询也已验证；入口为 api.main:app，原 main.py 仅打印欢迎语。未运行上游所有业务域测试。

## 操作边界

采购员提交申请，另一位审批员批准，再由采购员确认执行。执行前重查原数据指纹，数据变化则重提审批；执行后修改本地销售订单供货安排，扣减候选数量和预算，保存审计；SQLite 多订单写入失败会回滚。

历史采购单保留为最初来源，不会被改写成新供应商的采购单。本例不自动生成正式新采购单，也没有接真实 ERP。操作闭环由确定性测试验证，真实模型验证聚焦查询和评估。上游的角色参数和确认机制不能作为生产身份认证；不进行跨物料全局排产或采购优化。

## 流式对话与聚合展示

刷新页面后发起新问题，即可看到执行步骤、工具轨迹和逐步生成的回答。展开“查询与计算步骤”可看实际执行状态；这是可核查的过程摘要，不是模型完整内部思维链。模型仍使用非思考模式，未转发 `reasoning_content`。首次对话也使用同一条 POST `/api/chat/live` 数据流，不依赖先获得会话 ID 再连接另一个通道；原 `/api/chat` JSON 接口保留用于兼容。

可以直接问：

- “全部销售订单按物料汇总，展示金额排名、单数、件数与总计。”——48 单、10,450 件、883,250 元。
- 接着问：“只看 MAT-001，改为按客户汇总。”——8 单、1,700 件、119,000 元。
- “受延期影响的销售订单按供应商汇总。”——8 单、1,900 件、277,000 元。
- “采购单按供应商展示金额前 5 名，给出全量合计。”——采购单全量 18 单、29,880 件、2,222,000 元；全量有 6 个供应商分组，展示前 5 组。

这些是初始快照的结果；执行采购变更后应以当前数据库为准。`aggregateOrders` 支持销售/采购两种独立口径，按供应商、物料、状态分组，销售还可按客户分组；支持等值筛选、销售延期影响筛选与金额降序 Top N。它不是任意 SQL、任意字段或任意图表生成器。AI 选择函数与参数，程序计算汇总，界面直接将结果画成条形图和表格。图表及步骤随会话保存；断线或模型出错不会把未完成回答保存为成功结果。

采用 [LangChain 流式消息](https://reference.langchain.com/python/langchain-core/messages/ai/AIMessageChunk) 合并工具参数增量，复用上游工具、Runtime、权限和审计；本地适配的流式工具循环取代浏览器入口原有的阻塞调用。
