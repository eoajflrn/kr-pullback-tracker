"""Run completed KST date; never reuse stale data as today's discovery."""
import datetime,subprocess,sys
from run import KST,ROOT

def completed_date(now):
    return (now.date() if now.hour>=19 else now.date()-datetime.timedelta(days=1)).isoformat()

if __name__=='__main__':
    day=completed_date(datetime.datetime.now(KST))
    raise SystemExit(subprocess.call([sys.executable,str(ROOT/'run.py'),'--date',day,'--workers','8']))
