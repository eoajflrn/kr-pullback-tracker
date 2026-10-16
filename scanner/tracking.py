"""Latest prices for historical cohorts; never mutate historical signal decisions."""
import json,datetime

def register_snapshots(db,root):
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS tracking_targets(code TEXT PRIMARY KEY,name TEXT,market TEXT)')
        for path in sorted((root/'web/data/scans').glob('*.json')):
            for x in json.loads(path.read_text(encoding='utf-8')).get('stocks',[]):
                db.execute('INSERT OR IGNORE INTO tracking_targets VALUES(?,?,?)',(x['code'],x['name'],x.get('market','')))

def export_tracking(db,root):
    from run import atomic
    register_snapshots(db,root)
    rows=db.execute('SELECT code,name,market FROM tracking_targets UNION SELECT code,name,market FROM discoveries').fetchall()
    sessions=[r[0] for r in db.execute('SELECT date FROM sessions ORDER BY date')]
    stocks={}
    for r in rows:
        code=r[0];bars=[json.loads(b[0])for b in db.execute('SELECT payload FROM prices WHERE code=? ORDER BY date',(code,))]
        warnings=[r[0]for r in db.execute('SELECT DISTINCT reason FROM issues WHERE code=?',(code,))]
        stocks[code]=dict(code=code,name=r[1],market=r[2],bars=bars,warnings=warnings)
    out=dict(as_of=sessions[-1] if sessions else None,sessions=sessions,stocks=stocks,generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    atomic(root/'web/data/tracking.json',out)
    from scanner.analytics import export_analytics
    export_analytics(db,root,out)
    return out
