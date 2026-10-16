import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from scanner.store import connect
from scanner.tracking import export_tracking
class WindowsEncodingTest(unittest.TestCase):
 def test_korean_snapshot_with_cp949_default(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);(root/'web/data/scans').mkdir(parents=True)
   snap={'meta':{'as_of':'2026-10-13','mode':'RECONSTRUCTED','status':'SUCCESS'},'stocks':[{'code':'000010','name':'한글종목','market':'KOSPI','first_price':100,'first_date':'2026-10-13','signal_date':'2026-10-01','type':'B'}]}
   (root/'web/data/scans/2026-10-13.json').write_text(json.dumps(snap,ensure_ascii=False),encoding='utf-8')
   original=Path.read_text
   def windows_read(path,encoding=None,errors=None):return original(path,encoding=encoding or 'cp949',errors=errors)
   db=connect(':memory:')
   with patch.object(Path,'read_text',windows_read):export_tracking(db,root)
   result=json.loads((root/'web/data/analytics.json').read_text(encoding='utf-8'));self.assertEqual(result['rows'][0]['name'],'한글종목');db.close()
