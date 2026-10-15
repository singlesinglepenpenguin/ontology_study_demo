"""Demo POST-SSE adapter: real model deltas and observable tool execution."""
import asyncio
import json
import logging
import uuid

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, message_chunk_to_message
from ontopilot.prompt import PromptBuilder
from ontopilot.tools import create_tools
from runtime import build_runtime

log = logging.getLogger(__name__)


async def stream_turn(runtime, llm, session, message, history, confirmed, emit):
    turn_id = str(uuid.uuid4())
    runtime._event_callback = lambda event: emit("trace", event)
    emit("progress", {"text": "正在加载本体定义、角色权限和业务上下文"})
    role = session["role"]
    governance = runtime._governance
    tools = create_tools(runtime, session["user_id"], role, turn_id)
    tool_map = {tool.name: tool for tool in tools}
    prompt = PromptBuilder(runtime._schema, governance).build_system_prompt(
        role, session["warehouse_id"],
        runtime.build_context(session["user_id"], role, session["warehouse_id"], turn_id),
        governance.get_allowed_functions(role), list(governance._role(role).get("actions", {})),
    )
    prompt += "\n用户要求汇总、排名、图表时调用 aggregateOrders，金额与数量以函数结果为准。不要自行编写代码或SQL。全程使用中文。图表与明细表已由界面根据函数结果展示，回答只解释关键结论，无需重复绘制ASCII图表。"
    if confirmed and session.get("pending_action"):
        message = f"[用户已确认] {message}\n确认执行: {session['pending_action']}"
    messages = [SystemMessage(content=prompt), *history, HumanMessage(content=message)]
    model = llm.bind_tools(tools)
    response_parts = []
    for round_index in range(12):
        emit("progress", {"text": "正在选择查询与计算工具" if round_index == 0 else "正在核对工具结果并组织回答"})
        combined = None
        text_started = False
        async for chunk in model.astream(messages):
            combined = chunk if combined is None else combined + chunk
            # Only public answer content. Never forward reasoning_content or raw chunks.
            if isinstance(chunk.content, str) and chunk.content:
                if not text_started and response_parts:
                    response_parts.append("\n\n")
                    emit("answer_delta", {"text": "\n\n"})
                text_started = True
                response_parts.append(chunk.content)
                emit("answer_delta", {"text": chunk.content})
        if combined is None:
            raise RuntimeError("Empty model stream")
        answer = message_chunk_to_message(combined)
        messages.append(answer)
        if not answer.tool_calls:
            break
        for call in answer.tool_calls:
            name = call["name"]
            args = call["args"]
            label = args.get("function_name", args.get("object_type", args.get("action_name", name)))
            emit("progress", {"text": f"正在执行 {label}", "tool": name, "arguments": args})
            try:
                result = tool_map[name].invoke(args)
            except (KeyError, ValueError, TypeError) as exc:
                result = {"error": str(exc)}
            content = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
            messages.append(ToolMessage(content=content, tool_call_id=call["id"]))
            if name == "call_function" and args.get("function_name") == "aggregateOrders":
                data = json.loads(content) if isinstance(result, str) else result
                if isinstance(data, dict) and "rows" in data:
                    emit("visualization", data)
    else:
        raise RuntimeError("Tool round limit reached")
    traces = [e.to_dict() for e in runtime.get_trace_events(turn_id)]
    pending = next((e["input_summary"] for e in traces if e["status"] == "pending_confirmation"), None)
    return {"response": "".join(response_parts), "turn_id": turn_id,
            "trace_events": traces, "awaiting_confirmation": pending is not None, "pending_action": pending}


def register_stream(app, store):
    from api.schemas import ChatRequest
    busy = set()

    @app.post("/api/chat/live")
    async def live(body: ChatRequest):
        if body.model_id not in (None, "deepseek-flash-demo") or body.ontology_id not in (None, "ontology_schema.yaml"):
            raise HTTPException(400, "此示例仅支持当前本体和模型")
        if body.role not in ("viewer", "buyer", "approver"):
            raise HTTPException(400, "未知教学角色")
        sid = body.session_id
        if sid and not store.get(sid):
            raise HTTPException(404, "会话不存在，请新建对话")
        if not sid:
            sid = store.create_session(body.user_id, body.role, body.warehouse_id)
        session = store.get(sid)
        if session["user_id"] != body.user_id or session["role"] != body.role:
            raise HTTPException(403, "会话账号不匹配")
        if sid in busy:
            raise HTTPException(409, "此会话仍在处理中")
        busy.add(sid)
        history = store.get_history(sid)
        queue = asyncio.Queue()
        steps, charts = [], []
        def emit(kind, data):
            if kind == "progress":
                steps.append(data["text"])
            if kind == "visualization":
                charts.append(data)
            queue.put_nowait({"type": kind, **data})

        async def produce():
            try:
                # Isolated callback/tracer per request; same business SQLite database.
                result = await stream_turn(build_runtime(), app.state.active_llm, session,
                                           body.message, history, body.confirmed, emit)
                store.add_message(sid, "human", body.message)
                store.add_message(sid, "ai", result["response"])
                session["messages"][-1].update(steps=steps, charts=charts)
                store.update(sid, pending_action=result["pending_action"])
                emit("complete", {"session_id": sid, **result})
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Streaming chat failed")
                emit("error", {"message": "处理失败，本次回答未保存。请重试；若涉及写操作，先查询申请状态。"})
            finally:
                busy.discard(sid)
                queue.put_nowait(None)

        async def events():
            task = asyncio.create_task(produce())
            try:
                yield 'data: ' + json.dumps({"type": "session", "session_id": sid}) + '\n\n'
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15)
                    except asyncio.TimeoutError:
                        yield ': keepalive\n\n'
                        continue
                    if event is None:
                        break
                    yield 'data: ' + json.dumps(event, ensure_ascii=False) + '\n\n'
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                busy.discard(sid)
        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
