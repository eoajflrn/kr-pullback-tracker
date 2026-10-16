import unittest,tempfile,json
from pathlib import Path
from scanner.store import connect,ingest
from scanner.tracking import register_snapshots,export_tracking
from test_core import fixture
from scanner.core import signals
class TrackingTests(unittest.TestCase):
 def test_old_cohort_targets_survive_and_prices_continue(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);(p/'data').mkdir();(p/'web/data/scans').mkdir(parents=True)
   x=dict(code='000010',name='가상',market='KOSPI',first_price=110,first_date='2025-02-13');snap=json.dumps({'stocks':[x]});f=p/'web/data/scans/2025-02-13.json';f.write_text(snap)
   db=connect(p/'data/tracker.db');register_snapshots(db,p);register_snapshots(db,p)
   self.assertEqual(db.execute('select count(*) from tracking_targets').fetchone()[0],1)
   b=fixture();ingest(db,x,b,b[-1]['date'],[])
   later=dict(b[-1],date='2025-02-14',close=121,high=122);ingest(db,x,[later],later['date'],[])
   with db:db.executemany('insert into sessions values(?)',[(b[-1]['date'],),(later['date'],)])
   feed=export_tracking(db,p);self.assertEqual(feed['stocks']['000010']['bars'][-1]['close'],121)
   self.assertEqual(db.execute('select count(*) from discoveries').fetchone()[0],0)
   self.assertEqual(f.read_text(),snap)
   f.unlink();register_snapshots(db,p);self.assertEqual(db.execute('select count(*) from tracking_targets').fetchone()[0],1)
   db.close()
