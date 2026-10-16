function candleChart(x){
 const bars=(x.ohlcv||[]).filter(b=>b.high>=b.low&&b.low>0);if(!bars.length)return '<p>일봉 데이터 미확보</p>';
 const w=1000,h=440,left=65,right=920,top=25,bottom=305,low=Math.min(...bars.map(b=>b.low),x.first_price)*.98,high=Math.max(...bars.map(b=>b.high),x.first_price)*1.02;
 const X=i=>left+(i+.5)*(right-left)/bars.length,Y=v=>bottom-(v-low)/(high-low)*(bottom-top),cw=Math.max(1,(right-left)/bars.length*.65),maxv=Math.max(...bars.map(b=>b.volume),1);let svg='';
 for(let i=0;i<5;i++){const v=low+(high-low)*i/4;svg+=`<line x1="${left}" x2="${right}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e7ecf3"/><text x="${left-8}" y="${Y(v)+4}" text-anchor="end" font-size="12" fill="#67758a">${money(Math.round(v))}</text>`}
 bars.forEach((b,i)=>{const c=b.close>=b.open?'#ed4356':'#3576ce';svg+=`<g><title>${b.date} 시가 ${money(b.open)} 고가 ${money(b.high)} 저가 ${money(b.low)} 종가 ${money(b.close)} 거래량 ${money(b.volume)}</title><line x1="${X(i)}" x2="${X(i)}" y1="${Y(b.high)}" y2="${Y(b.low)}" stroke="${c}"/><rect x="${X(i)-cw/2}" y="${Math.min(Y(b.open),Y(b.close))}" width="${cw}" height="${Math.max(1,Math.abs(Y(b.open)-Y(b.close)))}" fill="${c}"/><rect x="${X(i)-cw/2}" y="${405-b.volume/maxv*65}" width="${cw}" height="${b.volume/maxv*65}" fill="${c}" opacity=".6"/></g>`});
 for(const [n,c]of [[20,'#e79819'],[60,'#7557ca']]){const pts=[];bars.forEach((b,i)=>{if(i>=n-1)pts.push(`${X(i)},${Y(bars.slice(i-n+1,i+1).reduce((s,p)=>s+p.close,0)/n)}`)});svg+=`<polyline points="${pts.join(' ')}" fill="none" stroke="${c}" stroke-width="1.7"/>`}
 svg+=`<line x1="${left}" x2="${right}" y1="${Y(x.first_price)}" y2="${Y(x.first_price)}" stroke="#67758a" stroke-dasharray="6 4"/>`;
 for(const [date,label,c]of [[x.signal_date,'급등봉','#7557ca'],[x.first_date,'기준일','#239d85']]){const i=bars.findIndex(b=>b.date===date);if(i>=0)svg+=`<line x1="${X(i)}" x2="${X(i)}" y1="15" y2="410" stroke="${c}" stroke-dasharray="3 4"/><text x="${Math.min(X(i),right-55)}" y="${label==='급등봉'?13:329}" font-size="12" fill="${c}">${label}</text>`}
 for(const i of [0,Math.floor(bars.length/2),bars.length-1])svg+=`<text x="${X(i)}" y="430" text-anchor="${i===0?'start':i===bars.length-1?'end':'middle'}" font-size="12" fill="#66758b">${bars[i].date}</text>`;
 return `<h3>일봉 · 거래량</h3><p class="hist">${bars.length}거래일 · MA20 주황 / MA60 보라 · 점선: 기준가격<br>확대·축소 또는 좌우 이동할 수 있습니다. 캔들에 마우스를 올리면 OHLCV가 표시됩니다.</p><div class="chart-actions"><button onclick="zoomChart(1.25)">확대 +</button><button onclick="zoomChart(.8)">축소 −</button><button onclick="document.querySelector('#candles').style.width='100%'">전체 보기</button></div><div class="chart-scroll"><svg id="candles" viewBox="0 0 ${w} ${h}" role="img" aria-label="일봉 캔들 거래량 차트">${svg}</svg></div>`;
}
function zoomChart(k){const el=document.querySelector('#candles');el.style.width=Math.max(700,Math.min(2800,(parseFloat(el.style.width)||1000)*k))+'px'}

function priceHistoryChart(x){
 const points=x.chart||[];if(!points.length)return '<p class="empty">가격 기록을 기다리고 있습니다.</p>';
 const base=x.first_price,values=points.map(p=>p.close).concat(base),lo=Math.min(...values)*.98,hi=Math.max(...values)*1.02;
 const X=i=>100+i/Math.max(1,points.length-1)*660,Y=v=>280-(v-lo)/(hi-lo)*200,ret=v=>x.warnings.length?null:(v/base-1)*100;
 const last=points.at(-1);
 let svg='<svg viewBox="0 0 900 350" role="img" aria-label="일별 종가와 발견가 대비 수익률">';
 for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4,y=Y(v);svg+=`<line x1="100" x2="760" y1="${y}" y2="${y}" stroke="#e2e7f0"/><text x="90" y="${y+5}" text-anchor="end" font-size="13" fill="#5c6b82">${money(Math.round(v))}원</text><text x="775" y="${y+5}" font-size="13" fill="#5c6b82">${pct(ret(v))}</text>`}
 svg+=`<line x1="100" x2="760" y1="${Y(base)}" y2="${Y(base)}" stroke="#8b9db9" stroke-dasharray="5 5"/><polyline points="${points.map((p,i)=>X(i)+','+Y(p.close)).join(' ')}" fill="none" stroke="#3563b5" stroke-width="3"/>`;
 points.forEach((p,i)=>{const label=points.length<=8||i===points.length-1;svg+=`<circle cx="${X(i)}" cy="${Y(p.close)}" r="4" fill="#3563b5"><title>${esc(p.date)} · ${money(p.close)}원 · ${pct(ret(p.close))}</title></circle>`;
 if(label)svg+=`<text x="${X(i)}" y="${Y(p.close)-25}" text-anchor="middle" font-size="14" font-weight="bold" fill="#253d65">${money(p.close)}원</text><text x="${X(i)}" y="${Y(p.close)-9}" text-anchor="middle" font-size="12" fill="#253d65">${pct(ret(p.close))}</text>`;
 if(points.length<=8||i===0||i===points.length-1)svg+=`<text x="${X(i)}" y="315" text-anchor="middle" font-size="12" fill="#5c6b82">${esc(p.date)}</text>`;
 });svg+='</svg>';
 return `<p class="history-summary">기준 ${esc(x.first_date)} · ${money(base)}원 → ${esc(last.date)} · ${money(last.close)}원 <span class="${tone(ret(last.close))}">${pct(ret(last.close))}</span></p><div class="history-chart">${svg}</div>`;
}
