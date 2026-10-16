import sqlite3,json,datetime

def connect(path):
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row;db.execute('PRAGMA synchronous=FULL')
    db.executescript('''CREATE TABLE IF NOT EXISTS discoveries(id TEXT PRIMARY KEY,code TEXT,name TEXT,market TEXT,first_date TEXT,first_price REAL,type TEXT,signal_date TEXT,captured_at TEXT,price_type TEXT);
CREATE TABLE IF NOT EXISTS exposures(id TEXT,date TEXT,type TEXT,PRIMARY KEY(id,date));
CREATE TABLE IF NOT EXISTS prices(code TEXT,date TEXT,close REAL,payload TEXT,PRIMARY KEY(code,date));
CREATE TABLE IF NOT EXISTS issues(code TEXT,date TEXT,reason TEXT,PRIMARY KEY(code,date,reason));
CREATE TABLE IF NOT EXISTS volume_snapshots(setup_id TEXT PRIMARY KEY,payload TEXT,provenance TEXT,recorded_at TEXT);
CREATE TABLE IF NOT EXISTS sessions(date TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY,requested_date TEXT,as_of TEXT,status TEXT,total INTEGER,checked INTEGER,missing INTEGER,detail TEXT,finished_at TEXT);''');return db

def ingest(db,stock,bars,day,found):
    code=stock['code'];now=datetime.datetime.now(datetime.timezone.utc).isoformat();conflict=False
    with db:
        for b in bars:
            old=db.execute('select close from prices where code=? and date=?',(code,b['date'])).fetchone()
            if old and abs(old[0]-b['close'])>.01:
                conflict=True;db.execute('insert or ignore into issues values(?,?,?)',(code,day,'가격 기준 변경 감지 — 분할/병합·수정주가 확인 필요'))
            db.execute('insert or ignore into prices values(?,?,?,?)',(code,b['date'],b['close'],json.dumps(b)))
        if len(bars)>1 and bars[-1]['date']==day and abs(bars[-1]['close']/bars[-2]['close']-1)>.35:
            conflict=True;db.execute('insert or ignore into issues values(?,?,?)',(code,day,'비정상 가격변동 — 기업행위 확인 필요'))
        if conflict:return
        for s in found:
            key=code+'_'+s['signal_date']
            db.execute('insert or ignore into discoveries values(?,?,?,?,?,?,?,?,?,?)',(key,code,stock['name'],stock['market'],day,bars[-1]['close'],s['type'],s['signal_date'],now,'NAVER_KRX_DAILY_CLOSE'))
            from scanner.analytics import volume_facts
            first=db.execute('select first_date from discoveries where id=?',(key,)).fetchone()[0]
            facts=volume_facts(bars,first,s['signal_date'])
            db.execute('INSERT OR IGNORE INTO volume_snapshots VALUES(?,?,?,?)',('OBSERVED_'+key,json.dumps(facts),'at_discovery' if first==day else 'stored_ohlcv_backfill',now))
            db.execute('insert or ignore into exposures values(?,?,?)',(key,day,s['type']))

def export(db,run):
    out=[];sessions=[r[0]for r in db.execute('select date from sessions order by date')]
    for d in db.execute('select * from discoveries order by first_date desc,code'):
        x=dict(d);bars=[dict(r)for r in db.execute('select date,close from prices where code=? and date>=? order by date',(x['code'],x['first_date']))]
        all_last=db.execute('select date,close from prices where code=? order by date desc limit 2',(x['code'],)).fetchall()
        warnings=[r[0]for r in db.execute('select distinct reason from issues where code=?',(x['code'],))]
        current=bars[-1] if bars else None;quality=not warnings and current is not None
        future=[d for d in sessions if d>x['first_date']];by={b['date']:b['close']for b in bars}
        x.update(current=current['close'] if current else None,price_date=current['date'] if current else None,return_pct=(current['close']/x['first_price']-1)*100 if quality else None,change_pct=(all_last[0]['close']/all_last[1]['close']-1)*100 if len(all_last)>1 and quality else None,elapsed=len([d for d in future if current and d<=current['date']]),warnings=warnings,chart=bars,last_seen=db.execute('select max(date) from exposures where id=?',(x['id'],)).fetchone()[0],exposures=[r[0]for r in db.execute('select date from exposures where id=? order by date',(x['id'],))])
        x['ohlcv']=[json.loads(r[0])for r in db.execute('select payload from prices where code=? and date<=? order by date',(x['code'],run.get('as_of') or '9999-12-31'))][-150:]
        x['returns']={str(n):(by[future[n-1]]/x['first_price']-1)*100 if quality and len(future)>=n and future[n-1]in by else None for n in [1,3,5,10]}
        out.append(x)
    return dict(meta=run,stocks=out)
