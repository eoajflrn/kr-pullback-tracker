"""Descriptive analytics only; never changes the signal rules."""
import json,datetime

def volume_facts(bars,day,signal):
    b=[x for x in bars if x['date']<=day];a=next((i for i,x in enumerate(b)if x['date']==signal),None)
    anchor=b[a]['volume']if a is not None else None
    prior=b[a-20:a]if a is not None and a>=20 else []
    avg=sum(x['volume']for x in prior)/20 if len(prior)==20 else 0
    return dict(anchor_volume=anchor,discovery_volume=b[-1]['volume']if b and b[-1]['date']==day else None,discovery_avg3_volume=sum(x['volume']for x in b[-3:])/3 if len(b)>=3 and b[-1]['date']==day else None,anchor_volume_multiple=anchor/avg if avg and anchor is not None else None,discovery_volume_dryup_pct=(sum(x['volume']for x in b[-3:])/3/anchor-1)*100 if anchor and len(b)>=3 and b[-1]['date']==day else None)

def covered(snapshot,code):
    if not snapshot:return False
    m=snapshot['meta']
    if m.get('limited')or m.get('status')not in ('SUCCESS','PARTIAL'):return False
    errors=m.get('errors',[])
    if any(not x.get('code')or x.get('code')==code for x in errors):return False
    return m.get('status')=='SUCCESS' or len(errors)>=m.get('missing',0)

def state_for(row,day,snapshots,sessions):
    seen=row['exposures'];prior=[d for d in sessions if d<day];prev=prior[-1]if prior else None
    group=row['origin'];maps=snapshots.get(group,{})
    if day in seen:
        if not any(d<day for d in seen):return '신규'
        if prev in seen:return '유지'
        return '재등장'if covered(maps.get(prev),row['code'])else'비교불가'
    if prev in seen and covered(maps.get(day),row['code']):return '이탈'
    return '미노출'if covered(maps.get(day),row['code'])else'비교불가'

def export_analytics(db,root,feed):
    from run import atomic
    with db:db.execute('CREATE TABLE IF NOT EXISTS volume_snapshots(setup_id TEXT PRIMARY KEY,payload TEXT,provenance TEXT,recorded_at TEXT)')
    snapshots={'OBSERVED':{},'RECONSTRUCTED':{}};records={}
    for d in db.execute('SELECT * FROM discoveries'):
        x=dict(d);x['origin']='OBSERVED';x['id']='OBSERVED_'+x['id'];x['exposures']=[r[0]for r in db.execute('SELECT date FROM exposures WHERE id=? ORDER BY date',(d['id'],))];records[x['id']]=x
    for p in sorted((root/'web/data/scans').glob('*.json')):
        snap=json.loads(p.read_text(encoding='utf-8-sig'))
        if not snap.get('meta',{}).get('as_of'):continue
        day=snap['meta'].get('as_of');origin='RECONSTRUCTED'if snap['meta'].get('mode')=='RECONSTRUCTED'else'OBSERVED'
        snapshots[origin][day]=snap
        if origin!='RECONSTRUCTED':continue
        for s in snap['stocks']:
            key=origin+'_'+s['code']+'_'+s['signal_date']
            if key not in records:records[key]=dict(s,id=key,origin=origin,first_date=day,first_price=next((b['close']for b in s.get('ohlcv',[])if b['date']==day),s['first_price']),exposures=[])
            records[key]['exposures'].append(day)
    sessions=feed['sessions'];latest=feed['as_of'];output=[]
    for x in records.values():
        b=feed['stocks'].get(x['code'],{});bars=b.get('bars',[]);saved=db.execute('SELECT payload,provenance FROM volume_snapshots WHERE setup_id=?',(x['id'],)).fetchone()
        if saved:
            facts=json.loads(saved[0]);provenance=saved[1]
            if 'discovery_volume'not in facts:
                additions=volume_facts(bars,x['first_date'],x['signal_date'])
                for key in ['anchor_volume','discovery_volume','discovery_avg3_volume']:facts[key]=additions[key]
                facts['absolute_volume_source']='stored_ohlcv_backfill'
                with db:db.execute('UPDATE volume_snapshots SET payload=? WHERE setup_id=?',(json.dumps(facts),x['id']))
        else:
            facts=volume_facts(bars,x['first_date'],x['signal_date']);provenance='stored_ohlcv_backfill'
            with db:db.execute('INSERT OR IGNORE INTO volume_snapshots VALUES(?,?,?,?)',(x['id'],json.dumps(facts),provenance,datetime.datetime.now(datetime.timezone.utc).isoformat()))
        last=bars[-1]if bars else None;warnings=b.get('warnings',[]);base=next((v for v in bars if v['date']==x['first_date']),None)
        valid=bool(last and base and x['first_price']>0 and not warnings and abs(base['close']-x['first_price'])<.01)
        future=[d for d in sessions if d>x['first_date']];by={v['date']:v['close']for v in bars};prev20=bars[-21:-1]if len(bars)>=21 else [];avg=sum(v['volume']for v in prev20)/20 if len(prev20)==20 else 0
        x.update(facts,volume_provenance=provenance,current=last['close']if last else None,price_date=last['date']if last else None,return_pct=(last['close']/x['first_price']-1)*100 if valid else None,latest_volume=last['volume']if last else None,latest_avg20_volume=avg if avg else None,latest_volume_multiple=last['volume']/avg if avg and last else None,elapsed=len([d for d in future if last and d<=last['date']]),warnings=warnings,last_seen=max(x['exposures'],default=None))
        after=[v for v in bars if v['date']>x['first_date']]
        peak=max(after,key=lambda v:v['high'])if after and valid else None
        peak_close=max(after,key=lambda v:v['close'])if after and valid else None
        x.update(peak_return_pct=(peak['high']/x['first_price']-1)*100 if peak else None,peak_date=peak['date']if peak else None,peak_price=peak['high']if peak else None,peak_close_return_pct=(peak_close['close']/x['first_price']-1)*100 if peak_close else None,peak_close_date=peak_close['date']if peak_close else None)
        x['returns']={str(n):(by[future[n-1]]/x['first_price']-1)*100 if valid and len(future)>=n and future[n-1]in by else None for n in [1,3,5,10]}
        x['peak_data_complete']=bool(after and last and last['date']==latest and all(d in by for d in future if d<=latest))
        x['states']={day:state_for(x,day,snapshots,sessions)for day in sorted(set(sessions)&set(snapshots[x['origin']]))}
        output.append(x)
    out=dict(as_of=latest,rows=output,dates=sorted(set(snapshots['OBSERVED'])|set(snapshots['RECONSTRUCTED'])))
    atomic(root/'web/data/analytics.json',out);return out
