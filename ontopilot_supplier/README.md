# OntoPilot 采购 Demo

这是一个独立运行的采购教学项目。后端、本体定义、170 条教学数据、前端源码和已构建页面均在本目录中，不需要另外 clone 上游项目，也不依赖目录外的 `repos`、Python 包源码或文件。

功能包括本体配置查看、SQLite 数据明细、真实模型流式问答、聚合图表，以及采购员提交申请、审批员批准、采购员确认执行。详见 [features.md](features.md)。

## 从 GitHub clone 后启动

需要 Python 3.11+，以下命令用于 macOS / Linux；Windows 可使用 WSL2。首次安装依赖需要联网，对话需要自己的 DeepSeek API Key。

```bash
git clone https://github.com/singlesinglepenpenguin/ontology_study_demo.git
cd ontology_study_demo/ontopilot_supplier
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
cp .env.example .env
```

编辑 `.env`，填写 `DEEPSEEK_API_KEY`，模型默认 `deepseek-v4-flash`。然后启动：

```bash
.venv/bin/python run.py serve
```

打开 **http://127.0.0.1:8000**。前端构建产物已经随项目提交，直接启动无需 Node.js。

| 角色 | 登录名 | 密码 |
|---|---|---|
| 查询员 | viewer | demo123 |
| 采购员 | buyer | demo123 |
| 审批员 | approver | demo123 |

首次启动会自动从 `config/seed_data.yaml` 初始化本地 SQLite；例如电芯受影响订单 O1/O2 共 1,000 件、70,000 元，FAST 替代方案额外成本 20,000 元，预算 30,000 元。不同账号的聊天隔离，业务申请按角色权限共享。

新 clone 的功能与本地服务一致，从初始教学业务数据开始；个人 API Key、已有对话、审批记录和本地测试结果不会上传。它们由本目录的 [.gitignore](.gitignore) 排除。

若端口冲突，可用 `run.py serve --port 8002`。若需要代理，在启动或安装前设置自己可用的代理地址，例如 `export all_proxy=http://127.0.0.1:7897`；项目不要求使用这个地址。

## 修改前端

需要 Node.js 20+。直接编辑 `frontend/src`，不再运行旧版补丁适配脚本：

```bash
cd frontend
npm ci
npm run build
cd ..
.venv/bin/python run.py serve
```

构建默认就是采购模式。提交前需要同时更新 `frontend/dist`，让其他人 clone 后无需额外构建。开发时可在后端运行的同时执行 `npm run dev`，访问其输出的开发地址。

## 重置教学数据

恢复初始业务数据但保留已有对话和审计：

```bash
.venv/bin/python run.py reset
```

这是显式重置命令；正常启动不会重置正在使用的业务数据。数据生成来源见 `dataset_manifest.json`；更新教学定义时运行 `build_dataset.py` 只重新生成配置文件。

## 代码来源

`ontopilot/`、`api/` 和前端基础代码来自 [jingw2/ontopilot](https://github.com/jingw2/ontopilot)，基于提交 `dc9ac375b979c7ea4fa95d209194f55b10f909f9` 适配。运行所需代码已包含在本目录；它是本地教学 Demo，不是 Palantir 官方产品，也未连接真实采购系统。
