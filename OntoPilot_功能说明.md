# OntoPilot 功能说明：原项目与当前采购 Demo

核对日期：2026-10-15。依据为本地克隆的上游提交 `dc9ac375b979c7ea4fa95d209194f55b10f909f9`、项目 [中文 README](repos/ontopilot/README.zh-CN.md)、实际源码，以及本地采购 Demo。本文按这一版本介绍功能，不代表上游最新版。配套阅读：[代码依赖图谱与阅读路线](OntoPilot_代码依赖图谱.md)。

## 1. 这个项目现在能干什么

OntoPilot 用 YAML 定义业务对象、属性、关系和允许调用的能力，再让 LLM 通过受控工具查数据、调用计算函数、预览和执行业务操作。它提供本体运行机制、Agent、API 和网页界面，具体业务算法仍由开发者实现。

当前打开 `http://127.0.0.1:8000`，运行的是我们基于它扩展的采购 Demo：可以查看采购业务全景，沿销售订单追溯采购来源，分析供应商延期影响，比较替代供货方案，按供应商、物料、客户等维度聚合并显示图表，还能按角色完成本地采购变更。会话只归当前登录账号，业务申请按权限共享。回答会逐步输出，并显示实际执行状态与工具轨迹。

**原项目提供通用框架和多个教学场景；当前网页固定使用采购 Demo，并没有把所有场景、管理功能都开放。** 它不是 Palantir 产品，也没有接入真实企业系统。所有当前业务数据均为教学数据。

## 2. 原项目的完整功能范围

下表的“原项目”表示源码中存在该能力；“当前 Demo”表示在我们实际启动的采购入口中的接入情况。源码存在不等于本次已完成全部场景的端到端验证。

| 功能 | 原项目如何实现 | 当前采购 Demo |
|---|---|---|
| 本体定义 | YAML 声明对象类型、主键、属性、外键关系、函数和操作 | 已加载 11 类对象、8 个函数、3 个操作 |
| 业务数据存储 | SQLite 保存对象 JSON，按类型和主键读取；YAML 导入种子数据 | 170 条初始记录，统一供应商和物料编号 |
| 对象查询 | 等值或列表条件过滤、字段投影、count 统计 | 已接入真实 Agent 查询 |
| 关系遍历 | 根据模型中的 foreign_key 找关联对象；多跳需要逐跳调用或业务函数组织 | `traceOrderRelations` 追溯订单、客户、物料、原采购单、批次、计划和评分 |
| 业务计算 | FunctionRegistry 把函数名映射到 Python 实现 | 延期、成本、预算、方案比较、聚合和风险评分 |
| LLM Agent | LangGraph 组织“调用模型→执行工具→再调用模型”的循环 | 浏览器使用新增流式循环，复用原工具和 Runtime；兼容接口保留原 Agent |
| 上下文构建 | 根据上下文 YAML 加入用户、角色、仓库和业务记录；PromptBuilder 生成提示词 | 补充采购对象定义、字段口径及业务限制 |
| 权限控制 | 按角色控制可查询类型、可调用函数、可执行操作；部分物流数据范围限制 | viewer、buyer、approver，分别承担查询、采购和审批 |
| 操作预览与确认 | preview_action 返回变更预览；执行时检查角色及确认要求 | 已接入；增加提交、异人审批、执行前重验及事务回滚 |
| 单步仿真 | 复制内存数据，在分支上比较物流运单方案的 KPI | 未接入采购浏览器场景；采购采用确定性方案评估函数 |
| 多轮会话 | SQLite 保存消息、标题和待确认操作；列表、打开、删除历史 | 已接入；保存步骤、聚合图表及实际工具返回；支持编辑标题，按登录账号隔离历史、读取、删除及续聊 |
| 执行 Trace | 记录上下文、查询、函数、操作、仿真等事件及输入输出摘要 | 实时进入页面；展示实际执行过程摘要 |
| 持久化审计 | 函数调用、操作执行等通过 AuditLogger 写 SQLite；提供查询接口 | 已复用；不是所有界面行为都构成审计事件 |
| 模型配置 | 模型列表、配置保存、连通性测试、切换；支持 Anthropic/OpenAI 及其兼容接口 | 固定本地配置的 DeepSeek；网页修改和测试模型接口未开放 |
| 本体管理 | 列表、状态、详情、YAML 上传、激活、删除和种子数据重载 | 固定采购本体自动加载，配置页显示后端状态，无需点击激活；提供只读元数据及教学数据重置，不开放任意上传或切换 |
| 用户与角色管理 | 教学登录、用户增删改查、角色权限读取和更新 | 固定三个教学账号，提供只读用户/角色信息 |
| 网页界面 | React 聊天、历史侧栏、模型与本体选择、管理页、Trace、本体关系图 | 已适配采购首页、10 个示例问题、流式聊天、聚合条形图和表格、只读 SQLite 数据明细 |
| REST API 与 SSE | FastAPI 路由；原 SSE 推送 Trace，POST chat 最后返回完整回答 | 新增单条 POST SSE，同时返回状态、Trace、文字增量、图表及完成事件 |
| 命令行 | `ontopilot chat` 与两个物流 `run_case` 示例 | `run.py` 提供 serve、chat、check、reset |
| 测试与评估 | 单元/集成/对话测试；BaselineEvaluator 检查数据、权限、确认、审计及范围 | 34 项程序测试，另有真实模型和浏览器验证 |

源码入口：[核心 Runtime](repos/ontopilot/ontopilot/runtime.py)、[原 API](repos/ontopilot/api/main.py)、[当前 Demo API](demo/ontopilot_supplier/server.py)。

### 2.1 本体与查询的具体能力

本体模型里的关系由目标类型和外键字段描述，例如 `Order.customer` 使用 `customerId` 找 Customer。数据里必须真的存在对应编号，连线才有实际意义。

对象查询支持按字段等值或列表过滤、只返回指定字段，以及 `aggregation="count"`。原 `object_query` 不是通用 SQL 引擎，没有任意 join、sum 或 group by；当前分组金额统计由新增 `aggregateOrders` 承担。

Runtime 和 ObjectStore 都有 `traverse` 方法，但原 Agent 暴露的五个工具中没有独立的 `traverse` 工具。Agent 可以根据编号多次查询，或调用我们写好的 `traceOrderRelations` 完成业务追溯。

来源：[模型解析](repos/ontopilot/ontopilot/schema.py)、[数据存储](repos/ontopilot/ontopilot/store.py)、[Agent 工具](repos/ontopilot/ontopilot/tools.py)。

### 2.2 Agent 可以调用哪五类工具

| 工具名 | 用途 | 是否改变正式业务数据 |
|---|---|---|
| object_query | 查询对象、过滤、字段选择、count | 否 |
| call_function | 调用已注册的业务函数 | 取决于函数实现；当前采购的 8 个函数均用于查询和计算 |
| preview_action | 展示操作将改变什么 | 否 |
| execute_action | 经权限和确认检查后执行操作 | 是 |
| simulate_decisions | 在数据分支中比较物流运单方案 | 不修改原业务对象 |

“工具可调用”还要经过 Runtime 的角色权限检查。写一个 YAML 函数名不会自动产生算法；必须同时存在对应 Python 实现及注册映射。

### 2.3 模型和 AI 用在哪里

当前真正调用 AI 的地方是对话：理解自然语言，确定要查的对象和函数参数，选择工具，结合结果回答和处理追问。流式文字也是模型实际返回的增量。

本体定义、数据生成、关系建立、金额汇总、风险规则、权限检查、审批和事务均由代码完成。当前没有“AI 自动搭建本体”、自动从文档抽取关系、文档 RAG、模型训练或机器学习预测。未来可以接入这些能力，但它们不是现在已经具备的功能。

页面显示的“查询与计算步骤”和“推理过程”来自执行状态与 Trace，不是模型完整内部思维链。当前 DeepSeek 的 thinking 模式仍关闭。

## 3. 原项目带了哪些业务场景

README 列出 5 个场景；本地 `config/` 实际还包含借贷场景，共 6 套业务模型。以下名称、对象和操作按实际 YAML 列出，避免沿用 README 中与代码不一致的示例。

| 场景与配置 | 对象类型 | 操作 |
|---|---|---|
| 基础关系：[ontology_schema.yaml](repos/ontopilot/config/ontology_schema.yaml) | Person、City、Company、Book | 无 |
| 人员与组织：[medium_ontology.yaml](repos/ontopilot/config/medium_ontology.yaml) | Person、Organization、City、Event、Publication | updatePersonInfo、transferEmployee |
| 项目与技能：[complex_ontology.yaml](repos/ontopilot/config/complex_ontology.yaml) | Person、Department、Project、Skill、Office、Meeting、Document、KPI | assignToProject、updateProjectStatus、promoteEmployee、transferOffice |
| 采购：[procurement_ontology.yaml](repos/ontopilot/config/procurement_ontology.yaml) | Material、Supplier、AllocationPlan、AllocationBatch、PurchaseOrder、SupplierScore | createAllocation、adjustBatch、confirmAllocation、scoreSupplier |
| 物流：[logistics_ontology.yaml](repos/ontopilot/config/logistics_ontology.yaml) | Shipment、Order、Customer、Carrier、Warehouse、ExceptionCase | createShipment、updateETA、assignCarrier、openExceptionCase |
| 借贷：[lending_ontology.yaml](repos/ontopilot/config/lending_ontology.yaml) | Borrower、LoanApplication、CreditReport、LoanContract、RepaymentPlan、RepaymentRecord、CollectionCase | submitApplication、runCreditCheck、approveLoan、rejectLoan、adjustLoanTerms、recordRepayment、openCollectionCase、applyCollectionStrategy |

复杂场景等配套种子、权限与上下文还分布在 `tests/test_data/`；切换时需要匹配整套配置。当前固定采购网页不承诺能直接切换上述所有场景。

### 3.1 原项目内置的全部 15 个业务函数

| 场景 | 函数名 | 功能 |
|---|---|---|
| 项目与技能 | calculateSkillGap | 计算项目技能需求与人员能力缺口 |
| 项目与技能 | findBestTeam | 根据所需技能推荐人员 |
| 项目与技能 | analyzeProjectHealth | 根据 KPI 等数据评估项目健康度 |
| 项目与技能 | getOrgChart | 返回组织与人员结构 |
| 采购 | recommendAllocation | 推荐供应商分货方案 |
| 采购 | analyzeSupplyRisk | 按规则计算供货风险 |
| 采购 | compareSupplierProposals | 比较供应商方案 |
| 采购 | calculateCostEfficiency | 计算采购成本效率 |
| 物流 | calculateDelayRisk | 计算运单延期风险 |
| 物流 | recommendCarrier | 推荐承运商 |
| 物流 | compareDecisions | 比较物流决策方案 |
| 借贷 | assessApplicationRisk | 评估贷款申请风险 |
| 借贷 | evaluateLoanPortfolio | 扫描贷款组合及还款风险 |
| 借贷 | compareLoanOptions | 比较贷款方案的月供、利息等指标 |
| 借贷 | compareCollectionOptions | 比较催收策略的估计结果 |

实现见 [functions.py](repos/ontopilot/ontopilot/functions.py)。这些是内置 Python 算法与规则，不应理解为已经训练好的行业预测模型；是否能在当前会话调用，还取决于场景和角色配置。

### 3.2 “单步仿真”实际做到哪一步

[simulation.py](repos/ontopilot/ontopilot/simulation.py) 会为每个候选方案复制一份对象数据，在副本中变更运单安排，再比较预计交付、延期小时数、成本变化、SLA 和客户风险。

当前实现围绕 Shipment、Carrier、Warehouse、Order 等物流对象，支持更换承运商、调整 ETA 这类方案。它采用平均运输时长和仓库积压等简化假设，不是通用仿真平台，也不是多步骤全局排程器。项目场景中有其他方案比较函数，不代表都经过这个仿真引擎。

## 4. 当前采购 Demo 的可用功能

### 4.1 数据和关系

初始共 170 条教学记录、11 类对象：Supplier 8、Material 6、Customer 12、Order 48、PurchaseOrder 18、AllocationPlan 10、AllocationBatch 21、SupplierScore 10、SupplyOption 36、Policy 1；ChangeRequest 初始为空，操作时生成。

34 条上游采购记录保留原有字段，其余为新增教学数据。销售需求与原采购台账共用供应商和物料编号，订单通过外键关联客户、物料、供应商和原采购单。记录来源见 [数据清单](demo/ontopilot_supplier/dataset_manifest.json)。

本体构建和数据关联由 [build_dataset.py](demo/ontopilot_supplier/build_dataset.py) 完成：合并原模型与扩展定义，生成数据，检查主键和关系目标，再输出供 Runtime 加载的 YAML。

### 4.2 当前可调用的全部 8 个函数

| 函数 | 可以问什么 | 返回内容 |
|---|---|---|
| getProcurementOverview | “采购业务全景怎么样？” | 各类对象数、延期影响、库存和预留 |
| assessSupplierDelay | “SUP-001 的 MAT-001 延期影响哪些订单？” | 受影响订单、件数、销售额和按物料汇总 |
| assessSupplyOption | “这个备选报价能接住这些订单吗？” | 物料、状态、交期、数量、成本与预算检查 |
| compareSupplyOptions | “这些候选方案怎么选？” | 同原供应商、同物料候选逐项检查并排序 |
| traceOrderRelations | “沿 O1 查客户和最初采购来源。” | 关联对象、原采购单、批次、计划和历史评分 |
| getChangeRequest | “这个变更申请到哪一步了？” | 申请状态及提交、审批、执行记录 |
| analyzeSupplyRisk | “PLAN-DEMO-RISK 为什么高风险？” | 原采购场景的确定性风险分数和原因 |
| aggregateOrders | “按供应商汇总，展示图表和总计。” | 分组单数、件数、金额、排名和全量合计 |

前 6 个及 aggregateOrders 的实现见 [domain.py](demo/ontopilot_supplier/domain.py)，analyzeSupplyRisk 复用原项目实现；注册接入见 [runtime.py](demo/ontopilot_supplier/runtime.py)。

### 4.3 聚合、展示和多轮追问

`aggregateOrders` 把销售订单 Order 与采购单 PurchaseOrder 分开计算。两者都能按供应商、物料、状态分组，销售还可以按客户分组。支持等值筛选、仅看延期影响销售订单、按金额降序展示 Top N。

图表是根据函数结果渲染的条形图和表格。Top N 只截取展示行，全量总计仍覆盖全部筛选记录。当前没有任意维度、任意 SQL 或任意图表自动生成功能。

| 可直接提的问题 | 初始快照结果 |
|---|---|
| 全部销售订单按物料汇总，展示排名和总计 | 48 单、10,450 件、883,250 元 |
| 接着问：只看 MAT-001，改为按客户汇总 | 8 单、1,700 件、119,000 元 |
| 受延期影响销售订单按供应商汇总 | 8 单、1,900 件、277,000 元 |
| 采购单按供应商展示金额前 5 名，并给全量合计 | 全量 18 单、29,880 件、2,222,000 元；展示 6 组中的前 5 组 |
| 只看供应商 SUP-999，按物料汇总 | 空分组，合计 0，不编造记录 |

执行变更后数字会随数据库变化；受影响销售额不是已经发生的损失。

### 4.4 方案比较与失败原因

- 电芯 MAT-001：SUP-001 延期影响 O1、O2，共 1,000 件、70,000 元。FAST 替代方案增加 20,000 元成本，初始预算为 30,000 元。
- 镜头 MAT-004：有受影响订单，但候选存在交期、数量或供应商状态问题，没有全量准时方案。
- 芯片 MAT-005：存在完整替代供货，但最低增量成本 32,000 元，超出预算。
- PLAN-DEMO-RISK：原规则给出 85 分。函数没有定义 100 分满分，不应自动写成 85/100 或 85% 概率。

这些判断是约束检查和规则计算，不是 AI 预测，也不代表全局最优采购或排产。

### 4.5 提交、审批和执行

| 账号 | 权限 | 密码 |
|---|---|---|
| viewer | 查询、聚合、追溯、评估 | demo123 |
| buyer | 查询评估、提交申请、执行已批准申请 | demo123 |
| approver | 查询评估、审批申请 | demo123 |

流程为：评估候选 → 预览并确认提交 `submitSupplierChange` → 另一位用户审批 `approveSupplierChange` → 采购员确认执行 `executeSupplierChange`。

执行前重新检查订单、报价、供应商和预算的数据指纹；审批后数据变化需要重新提交。执行会更新受影响销售订单的供货安排、扣减供货选项可用数量和预算，记录审计。SQLite 事务覆盖本例多订单写入，失败回滚。

原采购单保留为历史来源，不会自动生成正式新采购单或同步 ERP。操作闭环已由程序和 SQLite 集成测试验证，已在独立临时数据库中，通过真实 DeepSeek 与 Chrome 验证采购员提交、审批员批准、采购员执行的完整流程，每次操作均由用户预览确认；并非 Agent 自主批准。

### 4.6 流式对话、过程展示和历史

浏览器通过 POST `/api/chat/live` 在同一条流中接收会话编号、执行状态、Trace、回答文字增量、聚合数据和完成事件。首次提问也能实时显示进度。

步骤、图表和最终回答会随历史会话保存。模型失败或连接中断时，未完成回答不会被保存为成功结果。原 POST `/api/chat` 仍保留为兼容入口，返回完整 JSON。

右侧本体图主要展示**对象类型与关系定义**，结合 Trace 高亮涉及的类型；它不是展开全部 170 个实例的业务实例图。部分上游图高亮事件由函数返回的 involved_types 合成，不能据此认定每条连线都发生了独立数据库查询。

## 5. 当前不具备或尚未完整验证的能力

| 范围 | 实际边界 |
|---|---|
| 自动本体工程 | 没有可直接使用的 AI 自动建模、自动数据映射或本体自动治理流程 |
| 正式知识推理 | 使用 YAML、外键和 Python 规则，没有 OWL/RDF 推理器 |
| 文档检索 | 当前问答针对结构化对象，没有接向量库或文档 RAG |
| 外部执行 | 不连接真实 ERP、邮件、供应商平台，也不会实际下单 |
| 生产认证 | 教学登录已由服务端签发凭据，按账号隔离会话、校验角色；固定教学密码与本机服务仍不能作为生产身份系统 |
| 通用数据隔离 | 上游数据范围逻辑主要针对物流仓库；函数内部直接访问 Store，不能假设所有路径都有通用行级权限 |
| 通用工作流 | 没有可视化流程编排器；当前审批流程为专门实现 |
| 优化与预测 | 不做跨物料排程、全局采购优化、概率预测或自动训练 |
| 规模与稳定性 | 未完成长时间压力、生产并发或所有原项目场景的完整验证 |

## 6. 运行、验证与说明差异

从本工作区根目录启动当前已配置的 Demo：

```bash
export all_proxy=127.0.0.1:7897
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py serve
```

访问 http://127.0.0.1:8000，刷新页面后选择教学账号。新机器安装和前端构建请看 [Demo README](demo/ontopilot_supplier/README.md)。

本地验证记录：34 项程序测试、前次 7 组真实模型查询/评估、新增 6 组流式问答，以及 Chrome 页面验证。它们没有覆盖原项目所有业务域。详见 [验证记录](demo/ontopilot_supplier/验证记录.md) 和 [流式问答摘录](demo/ontopilot_supplier/流式问答验证.md)。

阅读原项目说明时注意三处差异：

1. README 的 `python main.py` 在此提交只打印欢迎语；原 FastAPI 入口为 `api.main:app`，应在原项目目录使用 `python -m uvicorn api.main:app --port 8000`，并先准备其配置。当前采购 Demo 使用上面的专门启动命令。
2. README 的“SSE 实时响应”在原聊天实现中主要指 Trace；文字生成使用同步 invoke，POST 最后返回完整答案。我们新增的采购流式入口才同时输出回答增量。
3. README 的场景数量、部分对象和操作名与配置不同。本文场景清单以本地 YAML 为准；存在测试脚本不等于那些测试已在本次全部运行并通过。


采购案例已按测试目标放入各账号历史，覆盖当前配置的全部 8 个业务函数与 3 个业务操作，详见 [对话案例清单](demo/ontopilot_supplier/对话案例清单.md)。每轮先读取共享申请最新状态，页面同时提供实时状态区；旧回答仍表示当时状态。完整写入流程的历史来自独立临时数据库，标题以“快照操作”区分，记录只读，当前业务使用新对话操作。
