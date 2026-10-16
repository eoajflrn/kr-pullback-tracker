/* Read-only analysis of immutable discovery cohorts. */
let analyticsFeed=null;
const multiple=v=>v==null?'미확인':Number(v).toFixed(2)+'배';
async function loadAnalytics(){try{analyticsFeed=await readJsonResponse(await fetch('data/analytics.json',{cache:'no-store'}));if(['ledger','changes','volume'].includes(tab)&&payload)render()}catch(e){analyticsFeed=null}}
const originalRender=render,originalDetail=detail;
render=function(){
 if(!['ledger','changes','volume'].includes(tab)){originalRender();return}
 $('.controls').hidden=false;
 const day=$('#asof').value||payload.meta.as_of;
 document.querySelector('h1').textContent=({ledger:'누적 발견 원장',changes:day+' 노출 변화',volume:'거래량별 성과'})[tab];
 $('#metrics').innerHTML='';$('#status').innerHTML='<p class="notice">동일 종목·동일 기준봉은 한 기록으로 유지합니다. 실제 발견과 과거 재계산은 별도 집계합니다. 최고 상승률은 발견 다음 거래일부터 최신 확보일까지의 고가 기준이며 실현수익이 아닙니다.</p>';
 if(!analyticsFeed){$('#result').innerHTML='<p>분석 자료를 불러오는 중입니다. 최신 PREVIEW.cmd로 실행해 주세요.</p>';return}
 const origin=document.querySelector('#origin')?.value||window.analysisOrigin||'OBSERVED';window.analysisOrigin=origin;
 let rows=analyticsFeed.rows.filter(x=>x.origin===origin&&(!$('#type').value||x.type===$('#type').value)&&(x.name+x.code).toLowerCase().includes($('#search').value.toLowerCase()));
 const toolbar='<div class="analysis-tools"><label>기록 구분 <select id="origin"><option value="OBSERVED">실제 발견</option><option value="RECONSTRUCTED">과거 재계산</option></select></label><button id="ledger-csv">현재 표 CSV</button></div>';
 if(tab==='changes')rows=rows.filter(x=>['신규','유지','재등장','이탈','비교불가'].includes(x.states?.[day])&&x.first_date<=day);
 rows.sort((a,b)=>$('#sort').value==='high'?(b.return_pct??-Infinity)-(a.return_pct??-Infinity):$('#sort').value==='low'?(a.return_pct??Infinity)-(b.return_pct??Infinity):b.first_date.localeCompare(a.first_date));
 let headers=['종목','최초 발견','유형','상태('+day+')','발견가','최근 종가','가격 기준일','누적수익률','최고 상승률(고가)','고가 날짜','최고값 자료','최고 상승률(종가)','종가 날짜','기준봉 거래량(주)','기준봉 배수','발견일 거래량(주)','발견시 3일평균(주)','발견 거래량 감소','최신 거래량(주)','직전20일 평균(주)','최신 배수','D+1','D+3','D+5','D+10','최근 노출'];
 let values=rows.map(x=>[x.name+' '+x.code,x.first_date,x.type,x.states?.[day]||'비교불가',money(x.first_price),money(x.current),x.price_date,pct(x.return_pct),pct(x.peak_return_pct),x.peak_date||'—',x.peak_data_complete?'기간 확보':'기간 미도래/부분자료',pct(x.peak_close_return_pct),x.peak_close_date||'—',money(x.anchor_volume),multiple(x.anchor_volume_multiple),money(x.discovery_volume),money(x.discovery_avg3_volume==null?null:Math.round(x.discovery_avg3_volume)),pct(x.discovery_volume_dryup_pct),money(x.latest_volume),money(x.latest_avg20_volume==null?null:Math.round(x.latest_avg20_volume)),multiple(x.latest_volume_multiple),...[1,3,5,10].map(n=>pct(x.returns?.[n])),x.last_seen]);
 let html='';
 if(tab==='volume'){
  headers=['발견 당시 감소율','전체 N','D+5 유효 N','D+5 평균','D+5 중앙값','D+5 상승 비율','D+10 유효 N','D+10 평균'];values=[];
  for(const [label,lo,hi]of [['-90% 이하',-Infinity,-90],['-90% 초과~-80%',-90,-80],['-80% 초과~-70%',-80,-70],['-70% 초과~-60%',-70,-60],['-60% 초과',-60,Infinity],['미확인',null,null]]){
   const g=rows.filter(x=>lo===null?x.discovery_volume_dryup_pct==null:x.discovery_volume_dryup_pct!=null&&x.discovery_volume_dryup_pct>lo&&x.discovery_volume_dryup_pct<=hi);
   const a=g.map(x=>x.returns?.['5']).filter(v=>v!=null).sort((a,b)=>a-b),b=g.map(x=>x.returns?.['10']).filter(v=>v!=null),avg=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null,med=a.length?(a[Math.floor((a.length-1)/2)]+a[Math.floor(a.length/2)])/2:null;
   values.push([label,g.length,a.length,pct(avg(a)),pct(med),a.length?(a.filter(v=>v>0).length/a.length*100).toFixed(1)+'%':'—',b.length,pct(avg(b))]);
  }
  html='<p>거래량 숫자는 주 단위이며 평균 거래량은 반올림합니다. 기존 기록의 추가 거래량 수치는 저장 일봉으로 소급 계산합니다.</p><p>기간 미도래·가격 오류는 수익률 0%로 채우지 않습니다. 동일 5·10거래일 종가 수익률을 비교하며 거래비용 전 수치입니다. 표본이 겹치는 종목은 서로 독립적인 표본이 아닙니다.</p>';
 }
 $('#result').innerHTML=toolbar+html+'<p>'+rows.length+'개 기록 · 가격 갱신 기준 '+esc(analyticsFeed.as_of)+' · 이탈은 추적 종료를 뜻하지 않습니다.</p><div class="analysis-scroll"><table class="analysis-table"><thead><tr>'+headers.map(v=>'<th>'+esc(v)+'</th>').join('')+'</tr></thead><tbody>'+values.map((v,i)=>'<tr>'+v.map((cell,j)=>'<td>'+((j===0&&tab!=='volume')?'<button data-analysis-id="'+esc(rows[i].id)+'">'+esc(cell)+'</button>':esc(cell))+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
 $('#origin').value=origin;$('#origin').onchange=e=>{window.analysisOrigin=e.target.value;render()};
 document.querySelectorAll('[data-analysis-id]').forEach(b=>b.onclick=()=>detail(rows.find(x=>x.id===b.dataset.analysisId)));
 $('#ledger-csv').onclick=()=>{const csv='\ufeff'+[headers,...values].map(row=>row.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')).join('\r\n');const u=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download=tab+'_'+day+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};
};
detail=function(x){originalDetail(x);const r=analyticsFeed?.rows.find(v=>v.code===x.code&&v.signal_date===x.signal_date&&v.first_date===x.first_date);if(!r)return;
 $('#detail-body').insertAdjacentHTML('beforeend','<h3>거래량 기록 · 발견 이후 최고 상승률</h3><div class="detail-grid">'+[['기준봉 거래량(주)',money(r.anchor_volume)],['발견일 거래량(주)',money(r.discovery_volume)],['발견시 최근3일 평균(주)',money(r.discovery_avg3_volume==null?null:Math.round(r.discovery_avg3_volume))],['최신 거래량(주)',money(r.latest_volume)],['직전20일 평균(주)',money(r.latest_avg20_volume==null?null:Math.round(r.latest_avg20_volume))],['기준봉 거래량 / 직전20일',multiple(r.anchor_volume_multiple)],['발견 당시 최근3일 / 기준봉 감소율',pct(r.discovery_volume_dryup_pct)],['최신 거래량 / 직전20일',multiple(r.latest_volume_multiple)],['최고 상승률 (장중 고가)',pct(r.peak_return_pct)+' · '+(r.peak_date||'기간 미도래 / 미확보')],['최고 상승률 (종가)',pct(r.peak_close_return_pct)+' · '+(r.peak_close_date||'기간 미도래 / 미확보')]].map(([a,b])=>'<div><small>'+esc(a)+'</small>'+esc(b)+'</div>').join('')+'</div><p>최고 상승률은 발견일 장중 고가를 제외하며 실제 매도수익이 아닙니다. 같은 최고값이 반복되면 첫 날짜를 표시합니다. 거래량 기록: '+esc(r.volume_provenance==='at_discovery'?'발견 시 저장':'기존 저장 일봉으로 소급 계산')+'</p>');};
loadAnalytics();
// Refresh derived reports after requests that can update stored prices.
for(const id of ['update-now','load-date','latest']){const b=$('#'+id),old=b.onclick;b.onclick=async(...a)=>{await old(...a);await loadAnalytics()}}
