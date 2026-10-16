"""Streaming/tool integration without a model or network."""
import asyncio
import tempfile
import unittest
from pathlib import Path
import run
from langchain_core.messages import AIMessageChunk
from runtime import build_runtime
from streaming import stream_turn


class StreamingTest(unittest.IsolatedAsyncioTestCase):
    async def test_progress_and_deltas_arrive_before_model_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            rt = build_runtime(Path(tmp) / 'test.db')
            events, gate = [], asyncio.Event()
            class Model:
                rounds = 0
                def bind_tools(self, tools, **kwargs): return self
                async def astream(self, messages):
                    self.rounds += 1
                    if self.rounds == 1:
                        yield AIMessageChunk(content='', tool_call_chunks=[{
                            'name': 'call_function', 'args': '{"function_name":"aggregateOrders",',
                            'id': 'tc1', 'index': 0}])
                        yield AIMessageChunk(content='', tool_call_chunks=[{
                            'name': None, 'args': '"params":{"affectedOnly":true}}', 'id': None, 'index': 0}])
                    else:
                        yield AIMessageChunk(content='受影响')
                        await gate.wait()
                        yield AIMessageChunk(content='8单，277000元')
            task = asyncio.create_task(stream_turn(rt, Model(),
                {'user_id': 'test', 'role': 'viewer', 'warehouse_id': ''}, '汇总影响', [], False,
                lambda kind, data: events.append((kind, data))))
            for _ in range(100):
                if any(kind == 'answer_delta' for kind, _ in events): break
                await asyncio.sleep(.01)
            self.assertFalse(task.done())
            self.assertTrue(any(kind == 'progress' for kind, _ in events))
            chart = next(data for kind, data in events if kind == 'visualization')
            self.assertEqual(chart['totals']['count'], 8)
            self.assertEqual(chart['totals']['amount'], 277000)
            actual = next(data for kind, data in events if kind == 'tool_result' and data['tool'] == 'call_function')
            self.assertEqual(actual['arguments']['function_name'], 'aggregateOrders')
            self.assertEqual(actual['result'], chart)
            gate.set()
            result = await task
            self.assertEqual(result['response'], '受影响8单，277000元')
            self.assertTrue(any(e['name'] == 'function:aggregateOrders' for e in result['trace_events']))

class StreamingHTTPTest(unittest.TestCase):
    def test_failure_has_no_complete_and_no_saved_answer(self):
        from unittest.mock import patch
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.routes.sessions import SessionStore
        from streaming import register_stream
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(str(Path(tmp) / 'sessions.db'))
            app = FastAPI()
            app.state.active_llm = object()
            from auth import register_auth
            register_auth(app, store)
            register_stream(app, store)
            async def fail(*args): raise RuntimeError('simulated provider failure')
            with patch('streaming.build_runtime', return_value=object()), patch('streaming.stream_turn', side_effect=fail), self.assertLogs('streaming', level='ERROR'):
                client = TestClient(app)
                client.post('/api/login', json={'username': 'viewer', 'password': 'demo123'})
                response = client.post('/api/chat/live', json={'role': 'viewer', 'user_id': 'viewer-demo', 'message': '测试'})
            import json
            events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
            self.assertEqual([e['type'] for e in events], ['session', 'error'])
            self.assertEqual(store.get(events[0]['session_id'])['messages'], [])
            self.assertEqual(client.post('/api/chat/live', json={'role': 'viewer', 'message': 'x', 'model_id': 'unknown'}).status_code, 400)
            self.assertEqual(client.post('/api/chat/live', json={'role': 'viewer', 'message': 'x', 'session_id': 'missing'}).status_code, 404)
            self.assertEqual(client.post('/api/chat/live', json={'role': 'viewer', 'user_id': 'other', 'message': 'x', 'session_id': events[0]['session_id']}).status_code, 403)
