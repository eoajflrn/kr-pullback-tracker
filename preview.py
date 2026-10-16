"""Local-only preview and date reconstruction. Never expose this service publicly."""
import http.server,json,threading,webbrowser,subprocess,sys,datetime,socket,argparse
from scanner.provider import Provider
from run import KST
from history import ROOT,reconstruct
lock=threading.Lock()
def update_latest():
    now=datetime.datetime.now(KST)
    cutoff=now.date() if now.hour>=19 else now.date()-datetime.timedelta(days=1)
    provider=Provider(ROOT)
    a=provider.bars('005930',cutoff.isoformat());b=provider.bars('000660',cutoff.isoformat())
    if not a or not b or a[-1]['date']!=b[-1]['date']:raise ValueError('최신 거래일을 확인하지 못했습니다. 기존 기록을 유지합니다.')
    day=a[-1]['date']
    log=ROOT/'data/manual_update.log'
    state_path=ROOT/'data/last_run.json'
    before=state_path.stat().st_mtime_ns if state_path.exists() else None
    with log.open('w',encoding='utf-8')as f:
        job=subprocess.run([sys.executable,str(ROOT/'run.py'),'--date',day],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    if job.returncode not in (0,1) or not state_path.exists() or state_path.stat().st_mtime_ns==before:
        raise ValueError('갱신 결과를 생성하지 못했습니다. 기존 기록을 유지합니다. data/manual_update.log를 확인하세요.')
    state=json.loads(state_path.read_text(encoding='utf-8'))
    if state.get('requested_date')!=day or state.get('status') not in ('SUCCESS','PARTIAL'):
        raise ValueError('갱신에 실패했습니다. data/manual_update.log를 확인하세요. 기존 기록은 보존됩니다.')
    return dict(date=day,message=f"{day} 기준 갱신 완료: 검사 {state['checked']}/{state['total']}종목, 미확보 {state['missing']}종목. 자동 예약 실행과는 별개입니다.")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'web'),**kw)
    def end_headers(self):
        self.send_header('Cache-Control','no-store');super().end_headers()
    def send_error(self, code, message=None, explain=None):
        if self.path.startswith('/api/'):
            messages={409:'다른 갱신 또는 날짜 재계산이 진행 중입니다. 완료 후 다시 조회하세요.',
                      403:'갱신과 과거 재계산은 PC의 localhost 화면에서 실행하세요. 휴대폰은 저장된 결과를 조회할 수 있습니다.',
                      404:'요청한 API가 없습니다. 최신 PREVIEW.cmd로 실행했는지 확인하세요.'}
            body=json.dumps({'error':messages.get(code,message or '요청 처리 실패'),'status':code},ensure_ascii=False).encode()
            self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        else:super().send_error(code,message,explain)
    def do_POST(self):
        if self.path not in ('/api/scan','/api/update'):self.send_error(404);return
        if self.client_address[0] not in ('127.0.0.1','::1'):self.send_error(403);return
        if self.headers.get('Host') not in ('127.0.0.1:8000','localhost:8000') or self.headers.get('Origin') not in (None,'http://127.0.0.1:8000','http://localhost:8000'):self.send_error(403);return
        if not lock.acquire(False):self.send_error(409,'Scan already running');return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<1000:raise ValueError('invalid request')
            request=json.loads(self.rfile.read(n))
            if self.path=='/api/update':r=update_latest();status=200
            else:
                day=request['date'];r=reconstruct(ROOT,day);status=200
        except Exception as e:r={'error':str(e)};status=400
        finally:lock.release()
        b=json.dumps(r,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b)
if __name__=='__main__':
    from scanner.store import connect
    from scanner.tracking import export_tracking
    db=connect(ROOT/'data/tracker.db');export_tracking(db,ROOT);db.close()
    parser=argparse.ArgumentParser();parser.add_argument('--lan',action='store_true');args=parser.parse_args()
    server=http.server.ThreadingHTTPServer(('0.0.0.0' if args.lan else '127.0.0.1',8000),Handler)
    if args.lan:
        addresses=set(socket.gethostbyname_ex(socket.gethostname())[2])
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as probe:
                probe.connect(('192.0.2.1',80));addresses.add(probe.getsockname()[0])
        except OSError:pass
        print('PHONE: same Wi-Fi; PC must stay on. Read-only. No router port forwarding.',flush=True)
        for ip in sorted(addresses):
            if not ip.startswith('127.'):print(f'PHONE URL: http://{ip}:8000/',flush=True)
    webbrowser.open('http://127.0.0.1:8000');print('http://127.0.0.1:8000');server.serve_forever()
