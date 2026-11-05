import os
import unittest
from unittest.mock import patch
from tests import test_storage
from tests.test_storage import authenticate


@unittest.skipUnless(os.getenv('WATCHDEMO_TEST_DATABASE_URL'), 'Explicit PostgreSQL URL required')
class ExportTests(unittest.TestCase):
    setUp=test_storage.PostgreSQLStorageTests.setUp
    tearDown=test_storage.PostgreSQLStorageTests.tearDown
    upload=test_storage.PostgreSQLStorageTests.upload
    analyze=test_storage.PostgreSQLStorageTests.analyze

    def test_owner_download_whitelists_fields_and_preserves_old_reports(self):
        result=dict(test_storage.RESULT)
        result['password_hash']='SECRET';result['stats']={'token':'SECRET'}
        result['report']={**result['report'],'session':'SECRET','summary':{'kills':3,'adr':42.5,'token':'SECRET','kd':{'token':'SECRET'}}}
        result['report']['top_problems']=[{'name':'Signal','score':2,'advice':[{'token':'SECRET'}],'internal':'SECRET'}]
        saved=self.analyze(self.upload(),result=result)
        response=self.client.get(f"/reports/{saved['report_id']}/export")
        self.assertEqual(response.status_code,200)
        self.assertIn('attachment;',response.headers['content-disposition'])
        self.assertEqual(response.json()['report']['summary'],{'kills':3,'adr':42.5})
        self.assertNotIn('SECRET',response.text)
        self.assertEqual(response.headers['cache-control'],'no-store')
        old=self.analyze(self.upload())
        self.assertEqual(self.client.get(f"/reports/{old['report_id']}/export").status_code,200)

    def test_only_owner_can_export_even_with_known_uuid(self):
        from fastapi.testclient import TestClient
        from app import create_app
        saved=self.analyze(self.upload())
        url=f"/reports/{saved['report_id']}/export"
        with TestClient(create_app(repository=self.repo,upload_dir=self.directory)) as other:
            self.assertEqual(other.get(url).status_code,401)
            authenticate(other,'other@example.com')
            self.assertEqual(other.get(url).status_code,404)

    def test_missing_or_failed_reports_are_not_downloadable(self):
        from uuid import uuid4
        self.assertEqual(self.client.get(f'/reports/{uuid4()}/export').status_code,404)
        uploaded=self.upload()
        with patch('app.analyze_demo',side_effect=ValueError('failure')):
            failed=self.client.post('/demo/analyze',json={'match_id':uploaded['match_id'],'steamid':test_storage.PLAYERS[0]['steamid']})
        report_id=failed.json()['detail']['report_id']
        self.assertEqual(self.client.get(f'/reports/{report_id}/export').status_code,409)
