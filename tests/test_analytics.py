import unittest,tempfile,json
from pathlib import Path
from scanner.analytics import volume_facts,state_for,export_analytics
from scanner.store import connect,ingest
from scanner.tracking import export_tracking
class AnalyticsTest(unittest.TestCase):
 def test_volume_no_future_or_anchor_in_average(self):
  bars=[dict(date=f'2026-01-{i+1:02}',volume=100)for i in range(20)]
  bars += [dict(date='2026-01-21',volume=1000)]+[dict(date=f'2026-01-{i}',volume=100)for i in [22,23,24]]
  facts=volume_facts(bars,'2026-01-24','2026-01-21');self.assertEqual(facts['anchor_volume'],1000);self.assertEqual(facts['discovery_volume'],100);self.assertEqual(facts['discovery_avg3_volume'],100);self.assertEqual(facts['anchor_volume_multiple'],10);self.assertEqual(facts['discovery_volume_dryup_pct'],-90)
  self.assertEqual(facts,volume_facts(bars+[dict(date='2026-01-25',volume=900000)],'2026-01-24','2026-01-21'))
 def test_lifecycle_missing_is_not_exit(self):
  sessions=['01','02','03','04'];snap={'OBSERVED':{d:{'meta':{'status':'SUCCESS'}}for d in sessions}}
  r=dict(code='000010',origin='OBSERVED',exposures=['01','02','04'])
  self.assertEqual([state_for(r,d,snap,sessions)for d in sessions],['신규','유지','이탈','재등장'])
  snap['OBSERVED']['03']={'meta':{'status':'PARTIAL','missing':1,'errors':[{'code':'000010'}]}}
  self.assertEqual(state_for(r,'03',snap,sessions),'비교불가');self.assertEqual(state_for(r,'04',snap,sessions),'비교불가')
 def test_peak_excludes_discovery_day_and_freezes_volume(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);(root/'web/data/scans').mkdir(parents=True);db=connect(':memory:')
   stock=dict(code='000010',name='test',market='KOSPI')
   bars=[dict(date=f'2026-01-{i+1:02}',open=100,high=110,low=90,close=100,volume=100)for i in range(24)]
   bars[20]['volume']=1000;bars[-1]['high']=200
   ingest(db,stock,bars,'2026-01-24',[dict(signal_date='2026-01-21',type='A')])
   later=[dict(bars[-1],date='2026-01-25',high=120,close=110,volume=100),dict(bars[-1],date='2026-01-26',high=120,close=105,volume=100)]
   ingest(db,stock,later,'2026-01-26',[])
   with db:db.executemany('insert into sessions values(?)',[(x['date'],)for x in bars+later])
   export_tracking(db,root);r=json.loads((root/'web/data/analytics.json').read_text())['rows'][0]
   self.assertAlmostEqual(r['peak_return_pct'],20);self.assertEqual(r['peak_date'],'2026-01-25');self.assertAlmostEqual(r['peak_close_return_pct'],10);self.assertAlmostEqual(r['return_pct'],5)
   stored=r['discovery_volume_dryup_pct'];export_tracking(db,root);self.assertEqual(json.loads((root/'web/data/analytics.json').read_text())['rows'][0]['discovery_volume_dryup_pct'],stored)
   self.assertEqual(db.execute('select count(*) from volume_snapshots').fetchone()[0],1)
