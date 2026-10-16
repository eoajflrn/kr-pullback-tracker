import unittest,tempfile,sqlite3,datetime
from pathlib import Path
from scanner.core import signals,validate
from scanner.store import connect,ingest,export

def fixture(age=3):
    # Synthetic sessions; algorithm boundary tests, never shown as market observations.
    n=40+age;b=[]
    for i in range(n+1):
        c=110 if i>=40 else 100
        b.append(dict(date=(datetime.date(2025,1,1)+datetime.timedelta(days=i)).isoformat(),open=99 if i==40 else c,high=c+1,low=98 if i==40 else c-1,close=c,volume=300 if i==40 else 100))
    return b
class Rules(unittest.TestCase):
    def test_A(self):self.assertEqual(signals(fixture())[0]['type'],'A')
    def test_exact_volume_boundary(self):
        b=fixture();
        for x in b[-3:]:x['volume']=120
        self.assertTrue(signals(b));b[-1]['volume']=120.1;self.assertEqual(signals(b),[])
    def test_average_excludes_signal(self):self.assertEqual(signals(fixture())[0]['volume_multiple'],3)
    def test_all_post_closes(self):
        b=fixture();b[-2]['close']=115;self.assertFalse(signals(b))
    def test_age_bounds(self):self.assertFalse(signals(fixture(2)));self.assertTrue(signals(fixture(10)))
    def test_b(self):self.assertEqual(signals(fixture(20))[0]['type'],'B')
    def test_a_b(self):
        b=fixture(9)
        for x in b[:39]:x.update(close=106,open=106,high=107,low=105)
        for x in b[41:]:x.update(close=107,open=107,high=108,low=106)
        self.assertEqual(signals(b)[0]['type'],'A+B')
    def test_b_ma_breach(self):
        b=fixture(20);b[42]['close']=95;self.assertFalse(signals(b))
    def test_bullish(self):
        b=fixture();b[40]['open']=110;self.assertFalse(signals(b))
    def test_future(self):
        b=fixture()
        with self.assertRaises(ValueError):validate(b,b[-2]['date'])
    def test_duplicate(self):
        b=fixture();b.append(b[-1]);
        with self.assertRaises(ValueError):validate(b,b[-1]['date'])
    def test_ohlc(self):
        b=fixture();b[-1]['low']=200
        with self.assertRaises(ValueError):validate(b,b[-1]['date'])
class Storage(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=connect(Path(self.tmp.name)/'x.db');self.b=fixture();self.s=dict(code='000010',name='가상',market='TEST');self.day=self.b[-1]['date'];ingest(self.db,self.s,self.b,self.day,signals(self.b))
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def test_idempotent(self):
        ingest(self.db,self.s,self.b,self.day,signals(self.b));self.assertEqual(self.db.execute('select count(*) from discoveries').fetchone()[0],1);self.assertEqual(self.db.execute('select count(*) from exposures').fetchone()[0],1)
    def test_departed_tracking(self):
        b=self.b+[dict(self.b[-1],date='2025-03-01',close=121,high=122)];ingest(self.db,self.s,b,'2025-03-01',[]);x=export(self.db,{})['stocks'][0];self.assertAlmostEqual(x['return_pct'],10);self.assertEqual(x['first_price'],110)
    def test_corporate_action(self):
        b=[dict(x)for x in self.b];b[-1]['close']=55;ingest(self.db,self.s,b,self.day,[]);x=export(self.db,{})['stocks'][0];self.assertIsNone(x['return_pct']);self.assertEqual(x['first_price'],110)
    def test_transaction(self):
        before=self.db.execute('select count(*)from prices').fetchone()[0]
        try:
            with self.db:self.db.execute('insert into prices values(?,?,?,?)',('x','x',1,'{}'));raise RuntimeError()
        except RuntimeError:pass
        self.assertEqual(before,self.db.execute('select count(*)from prices').fetchone()[0])
    def test_new_anchor(self):
        sig=dict(signals(self.b)[0],signal_date='2025-02-12');ingest(self.db,self.s,self.b,self.day,[sig]);self.assertEqual(self.db.execute('select count(*)from discoveries').fetchone()[0],2)
    def test_horizons_market_sessions(self):
        b=self.b+[dict(self.b[-1],date='2025-03-01',close=121,high=122)];ingest(self.db,self.s,b,'2025-03-01',[])
        with self.db:self.db.execute('insert into sessions values(?)',('2025-03-01',))
        x=export(self.db,{})['stocks'][0];self.assertAlmostEqual(x['returns']['1'],10);self.assertIsNone(x['returns']['3'])
if __name__=='__main__':unittest.main()
