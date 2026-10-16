import unittest,threading,json,http.client
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import preview

class ApiErrors(unittest.TestCase):
 def setUp(self):
  self.server=ThreadingHTTPServer(('127.0.0.1',0),preview.Handler)
  self.worker=threading.Thread(target=self.server.serve_forever,daemon=True);self.worker.start()
 def tearDown(self):self.server.shutdown();self.server.server_close();self.worker.join()
 def request(self,path,host='localhost:8000'):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
  c.request('POST',path,'{}',{'Host':host,'Content-Type':'application/json'})
  r=c.getresponse();result=(r.status,r.getheader('Content-Type'),json.loads(r.read()));c.close();return result
 def test_busy_json(self):
  preview.lock.acquire()
  try:
   status,kind,data=self.request('/api/scan');self.assertEqual(status,409);self.assertIn('json',kind);self.assertIn('진행 중',data['error'])
  finally:preview.lock.release()
 def test_forbidden_json(self):self.assertEqual(self.request('/api/update','evil.example')[0],403)
 def test_missing_api_json(self):self.assertEqual(self.request('/api/missing')[0],404)
 def test_update_success(self):
  with patch.object(preview,'update_latest',return_value={'message':'ok'}):self.assertEqual(self.request('/api/update')[2]['message'],'ok')
 def test_failed_job_releases_lock(self):
  with patch.object(preview,'update_latest',side_effect=ValueError('test error')):self.assertEqual(self.request('/api/update')[0],400)
  self.assertFalse(preview.lock.locked())
