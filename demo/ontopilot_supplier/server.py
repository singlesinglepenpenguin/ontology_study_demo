"""Reuse upstream chat, sessions, tracing and React UI for the supplier model."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from run import HERE, UPSTREAM, get_llm
from runtime import build_runtime, DEFAULT_DB


def create_app():
    # Upstream SessionStore uses a relative SQLite path at import time.
    os.chdir(HERE)
    from api.routes.chat import router as chat_router
    from api.routes.sessions import router as sessions_router
    from api.routes.audit import router as audit_router
    from api.routes.settings import router as settings_router
    from api.routes import chat, sessions
    sessions.session_store = sessions.SessionStore(str(DEFAULT_DB))
    chat.session_store = sessions.session_store
    import yaml

    def attach(app, reset=False):
        rt = build_runtime(reset=reset)
        app.state.runtime = rt
        app.state.schema = rt._schema
        app.state.governance = rt._governance
        app.state.audit_logger = rt._audit
        app.state.current_ontology_id = "ontology_schema.yaml"

    @asynccontextmanager
    async def lifespan(app):
        app.state.config_dir = str(HERE / "config")
        app.state.settings = yaml.safe_load((HERE / "config/settings.example.yaml").read_text())
        app.state.active_llm = get_llm()
        app.state._llm_cache = {"deepseek-flash-demo": app.state.active_llm}
        attach(app)
        yield

    app = FastAPI(title="OntoPilot 供应商延期教学示例", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def restrict_ontology(request: Request, call_next):
        # The upstream chat handler may otherwise rebuild the runtime with
        # built-in logistics functions when given a different ontology filename.
        if request.url.path == "/api/chat" and request.method == "POST":
            body = await request.json()
            if body.get("ontology_id") not in (None, "ontology_schema.yaml"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "此示例仅加载供应商本体"}, status_code=400)
            if body.get("model_id") not in (None, "deepseek-flash-demo"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "此示例使用本地配置的 DeepSeek 模型"}, status_code=400)
        return await call_next(request)

    app.include_router(chat_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(audit_router, prefix="/api")
    # Read-only metadata endpoints power the original ontology graph UI.
    for route in settings_router.routes:
        if getattr(route, "methods", set()) == {"GET"}:
            from fastapi import APIRouter
            readonly = APIRouter()
            readonly.routes.append(route)
            app.include_router(readonly, prefix="/api")

    demo_users = {
        "viewer": {"id": "viewer-demo", "username": "viewer", "role": "viewer", "display_name": "查询员"},
        "buyer": {"id": "buyer-demo", "username": "buyer", "role": "buyer", "display_name": "采购员"},
        "approver": {"id": "approver-demo", "username": "approver", "role": "approver", "display_name": "审批员"},
    }

    @app.post("/api/login")
    async def login(body: dict):
        user = demo_users.get(body.get("username"))
        if user is None or body.get("password") != "demo123":
            raise HTTPException(401, "教学账号为 viewer、buyer 或 approver，密码 demo123")
        return {"status": "ok", "user": user}

    @app.get("/api/users")
    async def users():
        return {"users": list(demo_users.values())}

    @app.get("/api/roles")
    async def roles():
        return yaml.safe_load((HERE / "config/permissions.yaml").read_text())

    @app.post("/api/ontology/activate")
    async def activate(body: dict, request: Request):
        if body.get("filename", "ontology_schema.yaml") != "ontology_schema.yaml":
            raise HTTPException(400, "此示例只加载供应商本体")
        return {"status": "ok", "message": "供应商本体已激活"}

    @app.post("/api/ontology/import")
    async def reset(request: Request):
        attach(request.app, reset=True)
        return {"status": "ok", "message": "教学数据已重置",
                "object_type_count": len(request.app.state.schema.object_type_names),
                "action_count": len(request.app.state.schema.action_names),
                "function_count": len(request.app.state.schema.function_names)}

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "ontology": "supplier-delay"}

    @app.get("/api/demo/overview")
    async def overview(request: Request):
        return request.app.state.runtime.call_function("demo-home", "viewer", "getProcurementOverview", {})

    dist = UPSTREAM / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
