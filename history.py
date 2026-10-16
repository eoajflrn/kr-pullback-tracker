"""Date snapshots are reconstructions, never new discovery-ledger entries."""
import argparse,datetime,json,sqlite3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from scanner.core import signals,validate
from scanner.provider import Provider
from scanner.store import connect,export
from run import ROOT,atomic,KST

def publish_index(root):
    folder=root/'web/data/scans';folder.mkdir(parents=True,exist_ok=True)
    atomic(root/'web/data/dates.json',{'dates':sorted(p.stem for p in folder.glob('????-??-??.json'))})

def reconstruct(root,day,network=True):
    datetime.date.fromisoformat(day)
    now=datetime.datetime.now(KST)
    if day>now.date().isoformat() or day==now.date().isoformat() and now.hour<19:raise ValueError('완료된 거래일만 선택하세요')
    provider=Provider(root);db=connect(root/'data/tracker.db');cached={}
    for row in db.execute('select code,payload from prices where date<=? order by code,date',(day,)):cached.setdefault(row['code'],[]).append(json.loads(row['payload']))
    known=[r[0] for r in db.execute('select date from sessions where date<=? order by date',(day,))]
    if day not in known:
        if not network:raise ValueError('거래일 데이터 미확보')
        b=provider.bars('005930',day)
        if not b or b[-1]['date']!=day:raise ValueError('휴장 또는 요청일 시세 미확보')
        known=[x['date'] for x in b]
    file=root/'data'/f'universe_{day}.json'
    if file.exists():u=json.loads(file.read_text(encoding='utf-8-sig'));universe=u['stocks'];source=u['source']
    else:
        universe,source=provider.universe(day,allow_live=False)
        atomic(file,dict(date=day,source=source,stocks=universe))
    eligible=[s for s in universe if s['code'].endswith('0') and s['cap']>=100_000_000_000]
    temp=connect(':memory:');errors=[];checked=0
    with temp:temp.executemany('insert into sessions values(?)',[(d,)for d in known])
    from scanner.store import ingest
    def fetch(s):
        b=cached.get(s['code'],[])
        if not b or b[-1]['date']!=day:
            if not network:raise ValueError('저장된 일봉 없음')
            b=provider.bars(s['code'],day)
        validate(b,day)
        if len(b)<30 or b[-1]['date']!=day:raise ValueError('30일 미만 이력 또는 요청일 일봉 없음')
        dates={x['date']for x in b}
        if any(d not in dates for d in known if d>=b[0]['date']):raise ValueError('거래일 누락')
        return b
    with ThreadPoolExecutor(12)as pool:
        futures={pool.submit(fetch,s):s for s in eligible}
        for f in as_completed(futures):
            s=futures[f]
            try:
                bars=f.result();found=signals(bars);checked+=1
                if found:
                    ingest(temp,s,bars,day,found)
                    ingest(db,s,bars,day,[]) # prices only; no backdated discoveries
            except Exception as e:errors.append(dict(code=s['code'],reason=str(e)))
    meta=dict(as_of=day,requested_date=day,status='PARTIAL' if errors else 'SUCCESS',total=len(eligible),checked=checked,missing=len(errors),errors=errors,mode='RECONSTRUCTED',cached_only=not network,finished_at=now.isoformat(),universe_source=source)
    result=export(temp,meta)
    atomic(root/'web/data/scans'/f'{day}.json',result);publish_index(root)
    from scanner.tracking import register_snapshots,export_tracking
    register_snapshots(db,root)
    # Refresh these historical candidates through latest known market session.
    latest=db.execute('select max(date) from sessions').fetchone()[0]
    if network and latest and latest>day:
        for x in result['stocks']:
            last=db.execute('select max(date) from prices where code=?',(x['code'],)).fetchone()[0]
            if last and last>=latest:continue
            try:
                b=provider.bars(x['code'],latest);validate(b,latest);ingest(db,x,b,latest,[])
            except Exception:pass # feed exposes old/missing date, never a false zero return
    export_tracking(db,root)
    db.close();temp.close()
    return dict(date=day,total=len(eligible),checked=checked,missing=len(errors),candidates=len(result['stocks']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--date');p.add_argument('--last',type=int,default=1);p.add_argument('--cached-only',action='store_true');a=p.parse_args()
    db=connect(ROOT/'data/tracker.db');dates=[a.date]if a.date else [r[0]for r in db.execute('select date from sessions order by date desc limit ?',(a.last,))];db.close()
    failed=False
    for d in sorted(dates):
        try:print(json.dumps(reconstruct(ROOT,d,not a.cached_only),ensure_ascii=False),flush=True)
        except Exception as e:failed=True;print(json.dumps(dict(date=d,error=str(e)),ensure_ascii=False),flush=True)
    if failed:raise SystemExit(1)
