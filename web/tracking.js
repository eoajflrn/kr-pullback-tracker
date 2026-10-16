/* Historical signals stay frozen. Only forward outcomes use this price feed. */
let trackingFeed=null;
function trackedRecord(x){
 const out={...x},p=trackingFeed?.stocks?.[x.code];
 if(!p){return {...out,current:null,price_date:null,return_pct:null,change_pct:null,returns:{1:null,3:null,5:null,10:null},warnings:[...(x.warnings||[]),'최신 추적 데이터 미확보'],chart:x.chart||[],ohlcv:x.ohlcv||[]}}
 const all=p.bars.filter(b=>b.date<=(trackingFeed.as_of||'9999-12-31')),bars=all.filter(b=>b.date>=x.first_date),last=bars.at(-1),prev=all.at(-2),warnings=[...new Set([...(x.warnings||[]),...(p.warnings||[])])];
 const base=all.find(b=>b.date===x.first_date);
 if(base&&Math.abs(base.close-x.first_price)>.01)warnings.push('기준가격과 저장 일봉 불일치 — 수정주가 확인 필요');
 const valid=last&&x.first_price>0&&!warnings.length;const sessions=(trackingFeed.sessions||[]).filter(d=>d>x.first_date);const by=new Map(bars.map(b=>[b.date,b.close]));
 out.current=last?.close??null;out.price_date=last?.date??null;out.return_pct=valid?(last.close/x.first_price-1)*100:null;out.change_pct=valid&&prev?(last.close/prev.close-1)*100:null;
 out.elapsed=sessions.filter(d=>last&&d<=last.date).length;out.warnings=warnings;out.chart=bars.map(b=>({date:b.date,close:b.close}));out.ohlcv=all.slice(-150);out.returns={};
 for(const n of [1,3,5,10])out.returns[n]=valid&&sessions.length>=n&&by.has(sessions[n-1])?(by.get(sessions[n-1])/x.first_price-1)*100:null;
 return out;
}
const WATCH_KEY='kr-pullback-watch-v1';let watchError='';
function getWatch(){try{const x=JSON.parse(localStorage.getItem(WATCH_KEY)||'[]');if(!Array.isArray(x))throw Error('invalid list');return x}catch(e){watchError='관심종목 저장소를 읽지 못했습니다.';return []}}
function writeWatch(list){try{localStorage.setItem(WATCH_KEY,JSON.stringify(list));watchError='';return true}catch(e){watchError='브라우저 저장에 실패했습니다. 저장 공간과 개인정보 설정을 확인하세요.';return false}}
function watchKey(x){return x.code+'_'+x.first_date}
function addWatch(x){const list=getWatch();if(!list.some(w=>w.watch_id===watchKey(x))){const saved={...x,watch_id:watchKey(x),added_at:new Date().toISOString(),origin:payload.meta.mode||'OBSERVED',id:watchKey(x)};delete saved.ohlcv;delete saved.chart;list.push(saved)}return writeWatch(list)}
function removeWatch(key){return writeWatch(getWatch().filter(w=>w.watch_id!==key))}
function watchRecords(){return getWatch().map(trackedRecord)}
function exportWatch(){const b=new Blob([JSON.stringify({version:1,watchlist:getWatch()},null,2)],{type:'application/json'}),u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download='관심종목_백업.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}
function importWatch(file){file.text().then(t=>{const obj=JSON.parse(t);if(obj.version!==1||!Array.isArray(obj.watchlist)||obj.watchlist.length>10000)throw Error('형식 오류');const list=getWatch();for(const w of obj.watchlist){if(typeof w.code!=='string'||!/^[A-Z0-9]{6}$/.test(w.code)||!/^\d{4}-\d{2}-\d{2}$/.test(w.signal_date)||!/^\d{4}-\d{2}-\d{2}$/.test(w.first_date)||!Number.isFinite(w.first_price)||w.first_price<=0||typeof w.name!=='string'||!['A','B','A+B'].includes(w.type))throw Error('유효하지 않은 항목');w.watch_id=watchKey(w);w.id=w.watch_id;w.exposures=Array.isArray(w.exposures)?w.exposures.filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d)):[];w.warnings=[];if(!list.some(x=>x.watch_id===w.watch_id))list.push(w)}if(writeWatch(list))render();else alert(watchError)}).catch(e=>alert('가져오기 실패: '+e.message))}

function dailyTable(x){return '<details class="daily-history" open><summary>일별 종가·누적수익률 보기 ('+x.chart.length+'일)</summary><table><thead><tr><th>거래일</th><th>종가</th><th>기준가 대비</th></tr></thead><tbody>'+x.chart.map(b=>{const r=x.warnings.length?null:(b.close/x.first_price-1)*100;return `<tr><td>${esc(b.date)}</td><td>${money(b.close)}</td><td class="${tone(r)}">${pct(r)}</td></tr>`}).join('')+'</tbody></table></details>'}
