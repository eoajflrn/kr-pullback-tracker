import unittest,tempfile,json,datetime
from pathlib import Path
from unittest.mock import patch,Mock
import preview
class Update(unittest.TestCase):
 def test_update_uses_provider_session(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'data').mkdir();(root/'data/last_run.json').write_text(json.dumps(dict(requested_date='2026-10-12',status='PARTIAL',checked=10,total=12,missing=2)))
   with patch.object(preview,'ROOT',root),patch.object(preview,'Provider')as p,patch.object(preview.subprocess,'run')as run:
    p.return_value.bars.return_value=[{'date':'2026-10-12'}]
    def finish(*args,**kwargs):
     import os
     path=root/'data/last_run.json';stamp=path.stat().st_mtime_ns+1000000;os.utime(path,ns=(stamp,stamp));return Mock(returncode=1)
    run.side_effect=finish
    result=preview.update_latest();self.assertEqual(result['date'],'2026-10-12');self.assertIn('2026-10-12',run.call_args[0][0])
 def test_crash_cannot_reuse_old_success(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'data').mkdir();(root/'data/last_run.json').write_text(json.dumps(dict(requested_date='2026-10-12',status='SUCCESS')))
   with patch.object(preview,'ROOT',root),patch.object(preview,'Provider')as p,patch.object(preview.subprocess,'run',return_value=Mock(returncode=1)):
    p.return_value.bars.return_value=[{'date':'2026-10-12'}]
    with self.assertRaises(ValueError):preview.update_latest()
 def test_mismatched_sessions_do_not_scan(self):
  with patch.object(preview,'Provider')as p,patch.object(preview.subprocess,'run')as run:
   p.return_value.bars.side_effect=[[{'date':'2026-10-12'}],[{'date':'2026-10-08'}]]
   with self.assertRaises(ValueError):preview.update_latest()
   run.assert_not_called()
