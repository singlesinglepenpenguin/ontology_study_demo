"""Compare inspection output against real SQLite, including changed records."""
import tempfile
import unittest
from pathlib import Path

import run
from fastapi import FastAPI
from fastapi.testclient import TestClient
from inspection import register_inspection
from runtime import build_runtime


class InspectionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rt = build_runtime(Path(self.tmp.name) / 'test.db')
        app = FastAPI()
        app.state.runtime = self.rt
        app.state.current_ontology_id = 'ontology_schema.yaml'
        register_inspection(app)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def data(self, filters=None, affected=False, **params):
        import json
        response = self.client.get('/api/demo/data', params={'filters': json.dumps(filters or {}),
                                   'affected_only': str(affected).lower(), **params})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_active_model_and_pagination_totals(self):
        for _ in range(2):
            model = self.client.get('/api/demo/model').json()
            self.assertEqual(model['activeOntology'], 'ontology_schema.yaml')
            self.assertEqual(len(model['objects']), 11)
            self.assertEqual(len(model['functions']), 8)
        data = self.data(limit=1)
        self.assertEqual(len(data['rows']), 1)
        self.assertEqual(data['totals']['count'], 48)
        self.assertEqual(data['totals']['amount'], 883250)
        purchases = self.data(object_type='PurchaseOrder')
        self.assertEqual(purchases['totals']['count'], 18)
        self.assertEqual(purchases['totals']['amount'], 2222000)

    def test_document_scopes_and_unaffected_control(self):
        chip = self.data({'supplierId': 'SUP-001', 'materialId': 'MAT-001'}, True)
        self.assertEqual({r['orderId'] for r in chip['rows']}, {'O1', 'O2'})
        self.assertEqual(chip['totals']['amount'], 70000)
        total = self.data({'supplierId': 'SUP-001'}, True)
        self.assertEqual({r['orderId'] for r in total['rows']}, {'O1', 'O2', 'O33', 'O34'})
        self.assertEqual(total['totals']['amount'], 160000)
        self.assertEqual(self.data(affected=True)['totals']['amount'], 277000)
        all_chips = self.data({'materialId': 'MAT-001'})
        self.assertEqual(all_chips['totals']['amount'], 119000)
        o3 = self.data({'orderId': 'O3'})
        self.assertFalse(o3['checks']['O3']['affected'])
        self.assertEqual(o3['rows'][0], self.rt._store.get('Order', 'O3'))

    def test_live_changes_and_readonly_route(self):
        original = self.rt._store.get('Order', 'O1')
        self.rt._store.update('Order', 'O1', {'salesAmount': 43000})
        current = self.data({'orderId': 'O1'})
        self.assertEqual(current['rows'][0]['salesAmount'], 43000)
        self.assertEqual(current['totals']['amount'], 43000)
        self.assertEqual(self.rt._store.get('Order', 'O1')['quantity'], original['quantity'])
        self.assertEqual(self.client.post('/api/demo/data', json={}).status_code, 405)

    def test_invalid_filters_and_empty_results(self):
        for params in ({'object_type': 'sessions'}, {'filters': '[]'}, {'filters': 'bad'},
                       {'filters': '{"unknown":"x"}'}, {'filters': '{"supplierId":["SUP-001"]}'},
                       {'object_type': 'Supplier', 'affected_only': 'true'}):
            self.assertEqual(self.client.get('/api/demo/data', params=params).status_code, 400)
        self.assertEqual(self.data({'supplierId': 'SUP-999'})['totals']['count'], 0)
