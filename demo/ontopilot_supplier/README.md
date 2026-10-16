# 采购 Demo

本机可运行的采购教学示例。供应商、订单和金额已经放在 `config/seed_data.yaml`，第一次启动会自动导入，不需要自己编数据。

使用前只需要准备你自己的 DeepSeek API Key。

## 启动

需要 Python 3.11 或更高版本。在 `demo/ontopilot_supplier` 目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
cp .env.example .env
```

编辑 `.env`，把 `DEEPSEEK_API_KEY` 换成你自己的 Key。模型名可以保持 `deepseek-v4-flash`。这个文件已被忽略，不要把它提交到 Git。

```bash
.venv/bin/python run.py serve
```

浏览器打开 http://127.0.0.1:8000 。

| 角色 | 登录名 | 密码 |
|---|---|---|
| 查询员 | viewer | demo123 |
| 采购员 | buyer | demo123 |
| 审批员 | approver | demo123 |

这个服务的功能详见 [features.md](features.md)：本体配置、数据明细、模型配置、用户管理，以及三个账号分别能做什么。

如果想把业务数据恢复成最初的教学记录，而保留已有对话：

```bash
.venv/bin/python run.py reset
```
