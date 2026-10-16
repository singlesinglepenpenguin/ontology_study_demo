"""Local demo login and server-enforced account ownership."""
import secrets
import time
from urllib.parse import parse_qsl, urlencode

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

USERS = {
    'viewer': {'id': 'viewer-demo', 'username': 'viewer', 'role': 'viewer', 'display_name': '查询员'},
    'buyer': {'id': 'buyer-demo', 'username': 'buyer', 'role': 'buyer', 'display_name': '采购员'},
    'approver': {'id': 'approver-demo', 'username': 'approver', 'role': 'approver', 'display_name': '审批员'},
}
COOKIE = 'supplier_demo_login'
TTL = 8 * 60 * 60


def register_auth(app, store):
    # Opaque server-issued credentials, kept only for this local server process.
    logins = {}

    def owns(session, identity):
        return session['user_id'] == identity['id'] and session['role'] == identity['role']

    @app.middleware('http')
    async def authenticate(request: Request, call_next):
        path = request.url.path
        if not path.startswith('/api/') or path in ('/api/login', '/api/health') or request.method == 'OPTIONS':
            return await call_next(request)
        token = request.cookies.get(COOKIE)
        login = logins.get(token)
        if not login or login['expires'] <= time.monotonic():
            if token:
                logins.pop(token, None)
            return JSONResponse({'detail': '请先登录；服务重启后需要重新登录。'}, status_code=401)
        identity = login['user']
        request.state.identity = identity
        sid = None
        if path in ('/api/chat', '/api/chat/live') and request.method == 'POST':
            try:
                body = await request.json()
            except ValueError:
                return JSONResponse({'detail': '请求正文必须是有效 JSON。'}, status_code=400)
            if isinstance(body, dict):
                if body.get('user_id', identity['id']) != identity['id'] or body.get('role', identity['role']) != identity['role']:
                    return JSONResponse({'detail': '请求账号与登录账号不一致，请重新登录。'}, status_code=403)
                sid = body.get('session_id')
        elif path == '/api/chat/stream':
            sid = request.query_params.get('session_id')
        if sid:
            session = store.get(sid)
            if session is not None and not owns(session, identity):
                return JSONResponse({'detail': '此会话属于其他账号，请使用自己的会话或新建对话。'}, status_code=403)
            if session is not None and any(message.get('caseContext') for message in session.get('messages', [])):
                return JSONResponse({'detail': '这是独立快照案例记录，请新建对话操作当前业务。'}, status_code=409)
        if path == '/api/audit':
            query = dict(parse_qsl(request.scope.get('query_string', b'').decode()))
            if query.get('user_id', identity['id']) != identity['id']:
                return JSONResponse({'detail': '不能读取其他账号的审计记录。'}, status_code=403)
            query['user_id'] = identity['id']
            request.scope['query_string'] = urlencode(query).encode()
        return await call_next(request)

    @app.post('/api/login')
    async def login(body: dict, request: Request):
        user = USERS.get(body.get('username'))
        if user is None or body.get('password') != 'demo123':
            raise HTTPException(401, '教学账号为 viewer、buyer 或 approver，密码 demo123')
        old = request.cookies.get(COOKIE)
        if old:
            logins.pop(old, None)
        now = time.monotonic()
        for expired in [key for key, value in logins.items() if value['expires'] <= now]:
            del logins[expired]
        token = secrets.token_urlsafe(32)
        logins[token] = {'user': dict(user), 'expires': now + TTL}
        response = JSONResponse({'status': 'ok', 'user': user})
        response.set_cookie(COOKIE, token, httponly=True, samesite='lax', max_age=TTL)
        return response

    @app.post('/api/logout')
    async def logout(request: Request):
        logins.pop(request.cookies.get(COOKIE), None)
        response = JSONResponse({'status': 'ok'})
        response.delete_cookie(COOKIE)
        return response

    def require_owned(sid, request):
        session = store.get(sid)
        if session is None:
            raise HTTPException(404, '会话不存在')
        if not owns(session, request.state.identity):
            raise HTTPException(403, '此会话属于其他账号，请使用自己的会话或新建对话。')
        return session

    @app.get('/api/sessions')
    async def list_sessions(request: Request):
        return {'sessions': [summary for summary in store.list_summaries()
                             if owns(summary, request.state.identity)]}

    @app.get('/api/sessions/{sid}')
    async def session_details(sid: str, request: Request):
        session = require_owned(sid, request)
        return {'session': {'id': sid, **{key: session.get(key) for key in
                ('title', 'created_at', 'updated_at', 'user_id', 'role', 'messages', 'pending_action')}}}

    @app.delete('/api/sessions/{sid}')
    async def delete_session(sid: str, request: Request):
        require_owned(sid, request)
        store.delete(sid)
        return {'status': 'ok', 'message': '会话已删除'}

    from pydantic import BaseModel, Field

    class RenameSession(BaseModel):
        title: str = Field(min_length=1, max_length=100)

    @app.patch('/api/sessions/{sid}')
    async def rename_session(sid: str, body: RenameSession, request: Request):
        require_owned(sid, request)
        title = body.title.strip()
        if not title:
            raise HTTPException(400, '会话标题不能为空')
        store.update(sid, title=title)
        return {'status': 'ok', 'id': sid, 'title': title}
