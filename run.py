import argparse,json,datetime,os,sys,traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
KST=datetime.timezone(datetime.timedelta(hours=9))
from scanner.core import signals,validate
from scanner.provider import Provider
from scanner.store import connect,ingest,export
from scanner.tracking import register_snapshots,export_tracking
ROOT=Path(__file__).resolve().parent

def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False),encoding='utf-8');os.replace(tmp,path)
def main():
    p=argparse.ArgumentParser();p.add_argument('--date');p.add_argument('--workers',type=int,default=8);p.add_argument('--limit',type=int);p.add_argument('--resume',action='store_true');p.add_argument('--audit-all',action='store_true');args=p.parse_args()
    now=datetime.datetime.now(KST);day=args.date or now.date().isoformat()
    if day>now.date().isoformat() or (day==now.date().isoformat() and now.hour<19):raise ValueError('장 마감 후 19시부터 실행')
    (ROOT/'data').mkdir(exist_ok=True);db=connect(ROOT/'data/tracker.db');provider=Provider(ROOT,reuse_raw=args.resume)
    backup=connect(ROOT/'data/backup.db');db.backup(backup);backup.close()
    register_snapshots(db,ROOT)
    run=dict(requested_date=day,as_of=None,status='FAILED',total=0,checked=0,missing=0,errors=[],finished_at=None,data_kind='REAL',limited=bool(args.limit))
    try:
        benchmarks=[provider.bars(c,day) for c in ['005930','000660']]
        if not all(b and b[-1]['date']==day for b in benchmarks):
            run.update(status='NO_NEW_SESSION',as_of=min((b[-1]['date']for b in benchmarks if b),default=None));raise RuntimeError('오늘 일봉 미확보 또는 휴장: 이전 후보를 오늘 신규로 만들지 않습니다')
        with db:db.executemany('insert or ignore into sessions values(?)',[(b['date'],)for b in benchmarks[0]])
        universe,source=provider.universe(day)
        if source=='NAVER_LIVE_UNIVERSE' and day!=now.date().isoformat():raise ValueError('과거일에 현재 시총 모집단 사용 금지')
        eligible=[s for s in universe if s['code'].endswith('0') and s['cap']>=100_000_000_000]
        run.update(as_of=day,universe_source=source,listed_total=len(universe),total=len(eligible))
        atomic(ROOT/'data'/f'universe_{day}.json',dict(date=day,source=source,stocks=universe))
        if args.limit:eligible=eligible[:args.limit]
        stocks={s['code']:s for s in eligible};screen_codes=set(stocks)
        tracked={r[0]for r in db.execute('select code from discoveries UNION SELECT code FROM tracking_targets')}
        for d in db.execute('select code,name,market from discoveries UNION SELECT code,name,market FROM tracking_targets'):stocks.setdefault(d['code'],dict(d))
        run['tracking_total']=len(stocks);failures=[]
        cached={}
        if args.resume:
            for row in db.execute('SELECT code,payload FROM prices WHERE date<=? ORDER BY code,date',(day,)):
                cached.setdefault(row['code'],[]).append(json.loads(row['payload']))
            cached={c:b for c,b in cached.items() if b[-1]['date']==day}
        def fetch(c):return cached[c] if c in cached else provider.bars(c,day)
        with ThreadPoolExecutor(max_workers=args.workers)as ex:
            futures={ex.submit(fetch,c):s for c,s in stocks.items()}
            for f in as_completed(futures):
                s=futures[f]
                try:
                    bars=f.result();validate(bars,day)
                    if not bars or bars[-1]['date']!=day:raise ValueError('오늘 일봉 없음')
                    if len(bars)<30:raise ValueError('30일 미만 이력')
                    # Missing sessions cannot silently shorten signal age.
                    dates={b['date']for b in bars};expected=[b['date']for b in benchmarks[0] if b['date']>=bars[0]['date']]
                    if any(d not in dates for d in expected):raise ValueError('거래일 누락 / 거래정지 점검 필요')
                    found=signals(bars)if s['code']in screen_codes else []
                    if args.audit_all or found or s['code']in tracked:ingest(db,s,bars,day,found)
                    if s['code']in screen_codes:run['checked']+=1
                except Exception as e:failures.append(dict(code=s['code'],reason=str(e)))
                if (run['checked']+len(failures))%100==0:print('progress',run['checked'],len(failures),len(stocks),flush=True)
        run.update(status='PARTIAL' if failures or args.limit else 'SUCCESS',missing=run['total']-run['checked'],errors=failures)
    except Exception as e:run['errors'].append(dict(reason=str(e)));print(str(e),file=sys.stderr)
    run['finished_at']=datetime.datetime.now(KST).isoformat()
    with db:db.execute('insert into runs(requested_date,as_of,status,total,checked,missing,detail,finished_at)values(?,?,?,?,?,?,?,?)',(day,run['as_of'],run['status'],run['total'],run['checked'],run['missing'],json.dumps(run,ensure_ascii=False),run['finished_at']))
    result=export(db,run)
    atomic(ROOT/'web/data/latest.json',result);
    if run['as_of']==day and run['status']in ('SUCCESS','PARTIAL'):
        snapshot=dict(result);snapshot['stocks']=[x for x in result['stocks'] if day in x['exposures']]
        snapshot['meta']=dict(run,mode='OBSERVED_SIGNALS')
        atomic(ROOT/'web/data/scans'/f'{day}.json',snapshot)
        from history import publish_index
        publish_index(ROOT)
    export_tracking(db,ROOT)
    atomic(ROOT/'data/last_run.json',run)
    print(json.dumps(run,ensure_ascii=False),flush=True);db.close()
    return 0 if run['status']in ('SUCCESS','NO_NEW_SESSION')else 1
if __name__=='__main__':sys.exit(main())
