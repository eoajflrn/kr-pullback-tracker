import urllib.request,json,ast,datetime,csv,io,hashlib,time,math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
class Provider:
    def __init__(self,root,reuse_raw=False):
        self.root=Path(root);self.archive=self.root/'data/raw';self.archive.mkdir(parents=True,exist_ok=True);self.cached={}
        if reuse_raw:
            for p in sorted(self.archive.glob('*.json'),key=lambda p:p.stat().st_mtime):
                try:self.cached[json.loads(p.read_text(encoding='utf-8-sig'))['url']]=p.with_suffix('.bin')
                except Exception:pass
    def get(self,url):
        if url in self.cached and self.cached[url].exists():return self.cached[url].read_bytes()
        error=None
        for attempt in range(2):
            try:
                b=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
                digest=hashlib.sha256(b).hexdigest();p=self.archive/(digest+'.bin')
                if not p.exists():p.write_bytes(b);p.with_suffix('.json').write_text(json.dumps({'url':url,'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}),encoding='utf-8')
                return b
            except Exception as e:error=e;time.sleep(attempt*.5)
        raise error
    def universe(self,day,allow_live=True):
        # Date-specific official FDR cache path verified in FinanceDataReader krx/listing.py.
        try:
            u=f'https://raw.githubusercontent.com/FinanceData/fdr_krx_data_cache/refs/heads/master/data/listing/krx/{day}.csv'
            rows=list(csv.DictReader(io.StringIO(self.get(u).decode('utf-8-sig'))))
            if not rows or not {'Code','Name','Marcap'}<=rows[0].keys():raise ValueError('listing schema')
            stocks=[dict(code=x['Code'],name=x['Name'],market=x.get('Market',''),cap=float(x['Marcap'])) for x in rows if x.get('MarketId')in ('STK','KSQ') or x.get('Market')in ('KOSPI','KOSDAQ','KOSDAQ GLOBAL')]
            if len(stocks)<500:raise ValueError('incomplete listing')
            return stocks,'FDR_KRX_DATE_CACHE'
        except Exception:
            if not allow_live:raise
            results=[]
            for market in ['KOSPI','KOSDAQ']:
                def page(p):return json.loads(self.get(f'https://m.stock.naver.com/api/stocks/marketValue/{market}?page={p}&pageSize=100'))
                first=page(1);total=int(first['totalCount']);parts=[first]
                with ThreadPoolExecutor(6) as ex:parts+=list(ex.map(page,range(2,math.ceil(total/100)+1)))
                stock=[x for part in parts for x in part['stocks']]
                if len({x['itemCode']for x in stock})!=total:raise ValueError('universe count mismatch')
                for x in stock:
                    if x.get('stockEndType')!='stock':continue # API also contains ETF/ETN
                    results.append(dict(code=x['itemCode'],name=x['stockName'],market=market,cap=float(str(x['marketValue']).replace(',',''))*1e8))
            return results,'NAVER_LIVE_UNIVERSE'
    def bars(self,code,day):
        start=(datetime.date.fromisoformat(day)-datetime.timedelta(days=220)).strftime('%Y%m%d')
        u=f'https://api.finance.naver.com/siseJson.naver?symbol={code}&requestType=1&startTime={start}&endTime={day.replace("-","")}&timeframe=day'
        a=ast.literal_eval(self.get(u).decode('utf-8-sig').strip());out=[]
        for x in a[1:]:
            d=str(x[0]);d=f'{d[:4]}-{d[4:6]}-{d[6:8]}'
            if d<=day:out.append(dict(date=d,open=float(x[1]),high=float(x[2]),low=float(x[3]),close=float(x[4]),volume=float(x[5])))
        return out
