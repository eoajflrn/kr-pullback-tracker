"""Pure rules. No network, no forward bars. Fractions are ratios, not percent points."""
def signals(bars):
    if len(bars)<30:return []
    t=len(bars)-1;out=[]
    ma=[sum(x['close'] for x in bars[i-19:i+1])/20 if i>=19 else None for i in range(len(bars))]
    for age in range(3,21):
        i=t-age
        if i<20:continue
        b=bars[i];prev=bars[i-1]['close'];avg=sum(x['volume']for x in bars[i-20:i])/20
        if prev<=0 or avg<=0 or b['close']<=b['open'] or b['close']/prev<1.10-1e-12 or b['volume']/avg<3-1e-12:continue
        dry=sum(x['volume'] for x in bars[-3:])/3/b['volume']
        if dry>0.4+1e-12:continue
        a=age<=10 and all(.96-1e-12<=x['close']/b['close']<=1.02+1e-12 for x in bars[i+1:])
        bb=age>=9 and ma[t]<=bars[t]['close']<=ma[t]*1.015+1e-12 and all(bars[j]['close']>=ma[j]-1e-12 for j in range(i+1,t+1))
        if a or bb:out.append(dict(signal_date=b['date'],type='A+B' if a and bb else 'A' if a else 'B',age=age,signal_return=b['close']/prev-1,volume_multiple=b['volume']/avg,volume_ratio=dry))
    # hsh chooses newest passing A first, otherwise newest B. Also report B when same anchor satisfies both.
    a=[x for x in out if 'A' in x['type']]
    return (a or out)[:1]

def validate(bars,as_of):
    import math
    seen=set()
    for b in bars:
        if b['date']>as_of or b['date']in seen:raise ValueError('future/duplicate bar')
        seen.add(b['date'])
        if not all(math.isfinite(b[k])for k in ['open','high','low','close','volume']):raise ValueError('nonfinite OHLC')
        if min(b[k]for k in ['open','high','low','close'])<=0 or b['volume']<0 or b['high']<max(b['open'],b['close'],b['low']) or b['low']>min(b['open'],b['close']):raise ValueError('invalid OHLC / suspension')
    if [b['date']for b in bars]!=sorted(seen):raise ValueError('unordered bars')
