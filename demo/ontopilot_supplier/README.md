# 采购 Demo

本机可运行的采购教学示例。供应商、订单和金额已经放在 `config/seed_data.yaml`，第一次启动会自动导入，不需要自己编数据。

使用前只需要准备你自己的 DeepSeek API Key。

## 启动

需要 Python 3.11 或更高版本。在本仓库根目录执行：

```bash
python3 -m venv repos/ontopilot/.venv
repos/ontopilot/.venv/bin/python -m pip install -r demo/ontopilot_supplier/requirements.lock.txt -e ./repos/ontopilot
cp demo/ontopilot_supplier/.env.example demo/ontopilot_supplier/.env
```

编辑 `demo/ontopilot_supplier/.env`，把 `DEEPSEEK_API_KEY` 换成你自己的 Key。模型名可以保持 `deepseek-v4-flash`。这个文件已被忽略，不要把它提交到 Git。

```bash
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py serve
```

浏览器打开 http://127.0.0.1:8000 。

| 角色 | 登录名 | 密码 |
|---|---|---|
| 查询员 | viewer | demo123 |
| 采购员 | buyer | demo123 |
| 审批员 | approver | demo123 |

各账号能看什么、能做什么，见同目录的《功能说明》。

如果想把业务数据恢复成最初的教学记录，而保留已有对话：

```bash
repos/ontopilot/.venv/bin/python demo/ontopilot_supplier/run.py reset
```
