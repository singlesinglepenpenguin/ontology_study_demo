"""Run from any working directory using OntoPilot's virtualenv Python."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load_env():
    # pip accepts a bare host:port proxy; httpx requires a URL scheme.
    for key in ("all_proxy", "ALL_PROXY", "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
        value = os.environ.get(key, "")
        if value and "://" not in value:
            os.environ[key] = "http://" + value
    settings = HERE / "config/settings.yaml"
    if not settings.exists():
        settings.write_text((HERE / "config/settings.example.yaml").read_text())
    path = HERE / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def get_llm():
    import yaml
    settings = yaml.safe_load((HERE / "config/settings.example.yaml").read_text())
    model = dict(settings["models"][0])
    model["model"] = os.environ.get("DEEPSEEK_MODEL", model["model"])
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("请在本目录 .env 中设置 DEEPSEEK_API_KEY")
    # Non-thinking mode avoids needing to relay DeepSeek reasoning_content
    # between tool calls in the upstream LangGraph loop.
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=model["model"], base_url=model["base_url"],
        api_key=os.environ["DEEPSEEK_API_KEY"], temperature=0,
        max_tokens=model["max_tokens"], timeout=90, max_retries=1,
        extra_body={"thinking": {"type": "disabled"}},
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check", "chat", "serve", "reset"])
    parser.add_argument("message", nargs="?")
    parser.add_argument("--role", choices=["viewer", "buyer", "approver"], default="viewer")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    load_env()
    if args.command == "serve":
        import uvicorn
        from server import create_app
        uvicorn.run(create_app(), host="127.0.0.1", port=args.port)
        return
    from runtime import build_runtime
    if args.command == "reset":
        build_runtime(reset=True)
        print("教学业务数据已重置；对话和审计记录保留。")
    elif args.command == "check":
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            runtime = build_runtime(Path(tmp) / "check.db")
            impact = runtime.call_function("viewer-demo", "viewer", "assessSupplierDelay", {"supplierId": "SUP-001", "materialId": "MAT-001"})
            option = runtime.call_function("viewer-demo", "viewer", "assessSupplyOption", {"supplierId": "SUP-001", "optionId": "OPT-MAT-001-FAST"})
            customer = runtime.traverse("viewer-demo", "viewer", "Order", "O1", "customer")
            assert impact["orderIds"] == ["O1", "O2"]
            assert impact["affectedSalesAmount"] == 70000
            assert option["extraCost"] == 20000 and option["feasible"]
            assert customer[0]["customerId"] == "C1"
            print(json.dumps({"impact": impact, "option": option, "customer": customer}, ensure_ascii=False, indent=2))
    else:
        if not args.message:
            parser.error("chat 需要提供问题")
        from ontopilot.agent import run_turn
        runtime = build_runtime()
        result = run_turn(
            runtime, get_llm(), runtime._schema, runtime._governance,
            f"{args.role}-demo", args.role, "", args.message,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
