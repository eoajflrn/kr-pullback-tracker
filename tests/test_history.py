import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from scanner.store import connect,ingest
from scanner.core import signals
from history import reconstruct
from test_core import fixture
class HistoryTests(unittest.TestCase):
    def test_reconstruction_isolated_and_no_future(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);(root/'data').mkdir();b=fixture();day=b[-1]['date'];stock=dict(code='000010',name='테스트',market='KOSPI',cap=200_000_000_000)
            db=connect(root/'data/tracker.db');ingest(db,stock,b,day,signals(b))
            with db:db.executemany('insert into sessions values(?)',[(x['date'],)for x in b])
            (root/'data'/f'universe_{day}.json').write_text(json.dumps(dict(source='TEST',stocks=[stock])))
            before=[tuple(x)for x in db.execute('select * from discoveries')]
            reconstruct(root,day,False);r=json.loads((root/'web/data/scans'/f'{day}.json').read_text())
            self.assertEqual(r['meta']['mode'],'RECONSTRUCTED');self.assertEqual(len(r['stocks']),1)
            self.assertTrue(all(x['date']<=day for x in r['stocks'][0]['ohlcv']))
            self.assertEqual(before,[tuple(x)for x in db.execute('select * from discoveries')]);db.close()
    def test_future_rejected(self):
        with tempfile.TemporaryDirectory()as d:
            with self.assertRaises(ValueError):reconstruct(Path(d),'2099-01-01',False)
