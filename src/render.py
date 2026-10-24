"""Render the single-file HTML dashboard from computed metrics."""

from __future__ import annotations

import json

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>股指期货贴水监控</title>
<style>
:root{
  --bg:#f4f6f9; --card:#fff; --ink:#16202e; --muted:#6b7684; --faint:#9aa4b2;
  --line:#e4e8ee; --up:#cf2f2f; --down:#12855a; --accent:#1f4e79; --warn:#d98207;
  --soft:#eef2f7;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{
  margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Segoe UI",Roboto,sans-serif;
  font-size:15px;line-height:1.6;
}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px 48px}
.topbar{height:3px;background:linear-gradient(90deg,#1f4e79,#3c7fb8 55%,#d98207)}
header{padding:22px 0 14px;display:flex;flex-wrap:wrap;align-items:flex-end;gap:10px;justify-content:space-between}
h1{font-size:20px;margin:0;letter-spacing:.5px;font-weight:650}
.sub{color:var(--muted);font-size:12.5px;margin-top:4px}
.stamp{font-size:12px;color:var(--faint);text-align:right;line-height:1.5}
.banner{
  background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);
  border-radius:10px;padding:14px 16px;margin:6px 0 18px;font-size:14.5px;
}
.banner b{font-weight:650}
.tabs{display:flex;gap:6px;margin-bottom:14px;overflow-x:auto;padding-bottom:2px}
.tab{
  flex:0 0 auto;padding:7px 15px;border-radius:8px;border:1px solid var(--line);
  background:var(--card);color:var(--muted);font-size:13.5px;cursor:pointer;
  transition:.15s;font-weight:500;
}
.tab.on{background:var(--accent);border-color:var(--accent);color:#fff}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:repeat(2,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card h3{margin:0 0 12px;font-size:13px;color:var(--muted);font-weight:600;letter-spacing:.4px}
.big{font-size:38px;font-weight:680;letter-spacing:-1px;line-height:1.1;font-variant-numeric:tabular-nums}
.big small{font-size:17px;font-weight:500;margin-left:2px}
.metric{font-size:12.5px;color:var(--muted);margin-top:6px}
.pill{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11.5px;font-weight:600;margin-top:8px}
.p-ok{background:#e6f4ec;color:var(--down)}
.p-mid{background:#fdf1dd;color:var(--warn)}
.p-bad{background:#fbe9e9;color:var(--up)}
.p-neutral{background:var(--soft);color:var(--muted)}
.mini{font-size:12px;color:var(--muted)}
.mini b{color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
th{text-align:right;color:var(--muted);font-weight:600;padding:7px 6px;border-bottom:1px solid var(--line);font-size:12px}
td{text-align:right;padding:8px 6px;border-bottom:1px solid #f1f4f8}
th:first-child,td:first-child{text-align:left}
tr:last-child td{border-bottom:none}
.chart{width:100%;height:290px}
.chart.sm{height:230px}
.calc-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
label{display:block;font-size:11.5px;color:var(--muted);margin-bottom:4px}
input{
  width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:8px;
  font-size:14px;font-variant-numeric:tabular-nums;background:#fbfcfd;color:var(--ink);
  font-family:inherit;
}
input:focus{outline:none;border-color:var(--accent);background:#fff}
.safe-row{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.safe-item{background:#fafbfd;border:1px solid var(--line);border-radius:9px;padding:11px 12px}
.safe-item .k{font-size:11.5px;color:var(--muted)}
.safe-item .v{font-size:19px;font-weight:650;margin-top:3px;font-variant-numeric:tabular-nums}
.note{font-size:12px;color:var(--faint);line-height:1.7;margin-top:12px}
.foot{margin-top:26px;padding-top:16px;border-top:1px solid var(--line);font-size:11.5px;color:var(--faint);line-height:1.75}
.up{color:var(--up)} .down{color:var(--down)} .muted{color:var(--muted)}
@media(max-width:820px){
  .g4{grid-template-columns:repeat(2,1fr)}
  .calc-grid,.safe-row{grid-template-columns:repeat(2,1fr)}
  .big{font-size:32px}
  .chart{height:250px}
}
@media(max-width:480px){
  .g2{grid-template-columns:1fr}
  body{font-size:14px}
  th,td{padding:6px 4px;font-size:12px}
}
</style>
</head>
<body>
<div class="topbar"></div>
<div class="wrap">
  <header>
    <div>
      <h1>股指期货贴水监控</h1>
      <div class="sub" id="subline"></div>
    </div>
    <div style="text-align:right">
      <a href="manual.html" style="font-size:12.5px;color:#1f4e79;text-decoration:none;border-bottom:1px solid #b8cfe0">实操手册 →</a>
      <div class="stamp" id="stamp"></div>
    </div>
  </header>

  <div class="banner" id="banner"></div>

  <div class="tabs" id="tabs"></div>

  <div class="grid g2" style="margin-bottom:14px">
    <div class="card">
      <h3>主力合约年化贴水</h3>
      <div class="big" id="mainAnn">--<small>%</small></div>
      <div class="metric" id="mainMeta"></div>
      <div id="annPill"></div>
    </div>
    <div class="card">
      <h3>换月窗口</h3>
      <div class="big" id="rollPct">--<small>%</small></div>
      <div class="metric" id="rollMeta"></div>
      <div id="rollPill"></div>
    </div>
  </div>

  <div class="card" style="margin-bottom:14px">
    <h3>主力合约年化贴水历史（近 244 个交易日）</h3>
    <div id="chartHist" class="chart"></div>
  </div>

  <div class="card" style="margin-bottom:14px">
    <h3>各期合约贴水对比 · 统一取剩余约 30 天时点（消除期限结构影响）</h3>
    <div id="chartContracts" class="chart sm"></div>
    <div class="note" style="margin-top:6px">每个柱代表一个交割月份的合约，取该合约剩余约 30 天那一天的读数 —— 统一了剩余期限，就能直接比较不同月份合约的贴水厚薄。注意：只显示已经走到剩余 30 天附近的合约，所以当前主力（剩余 50 天以上）不会出现在这张图上；红色柱表示它同时也是当前主力。柱子在 0 以下说明当期是<b>升水</b>，滚多头在这种合约上不但吃不到贴水，还要倒贴。</div>
  </div>

  <div class="card" style="margin-bottom:14px">
    <h3>期限结构斜率 · 下季 vs 当季（年化）</h3>
    <div id="chartSlope" class="chart"></div>
    <div class="note" style="margin-top:6px">斜率 =（下季价 − 当季价）÷ 当季价 × 365 ÷ 两个到期日之间的天数。<b>负得越多，说明远月比近月便宜得越多</b>，往远月换的补偿越厚；接近 0 说明期限结构平坦，换远月没有额外收益。大圆点为每月最后一个交易日的读数。</div>
  </div>

  <div class="grid g2" style="margin-bottom:14px">
    <div class="card">
      <h3>期限结构 · 各合约贴水</h3>
      <div id="chartTerm" class="chart sm"></div>
    </div>
    <div class="card">
      <h3>近月 − 次月 价差历史</h3>
      <div id="chartRoll" class="chart sm"></div>
    </div>
  </div>

  <div class="card" style="margin-bottom:14px">
    <h3>四品种横向对比</h3>
    <table id="cmpTable"></table>
  </div>

  <div class="card" style="margin-bottom:14px">
    <h3>持仓安全垫（本地计算，不上传）</h3>
    <div class="calc-grid">
      <div><label>本金（万元）</label><input id="inCap" type="number" step="1" value="50"></div>
      <div><label>手数</label><input id="inLots" type="number" step="1" value="1"></div>
      <div><label>开仓价（点）</label><input id="inOpen" type="number" step="0.2"></div>
      <div><label>保证金比例（%）</label><input id="inMargin" type="number" step="0.5" value="13"></div>
    </div>
    <div class="safe-row">
      <div class="safe-item"><div class="k">保证金占用</div><div class="v" id="oMargin">--</div></div>
      <div class="safe-item"><div class="k">占用率</div><div class="v" id="oUsed">--</div></div>
      <div class="safe-item"><div class="k">当前杠杆</div><div class="v" id="oLev">--</div></div>
      <div class="safe-item"><div class="k">距追保</div><div class="v" id="oBuf">--</div></div>
    </div>
    <div class="note" id="calcNote"></div>
  </div>

  <div class="card">
    <h3>合约明细</h3>
    <table id="ctTable"></table>
  </div>

  <div class="foot" id="foot"></div>
</div>

<script src="https://cdn.bootcdn.net/ajax/libs/echarts/5.5.0/echarts.min.js"></script>
<script>
if (typeof echarts === 'undefined') {
  document.write('<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"><\/script>');
}
</script>
<script>
const DATA = __DATA_JSON__;
const ORDER = ['IC','IM','IF','IH'];
let CUR = 'IC';
const charts = {};

function ensureChart(id, key) {
  if (typeof echarts === 'undefined') {
    const el = document.getElementById(id);
    if (el && !el.dataset.failed) {
      el.dataset.failed = '1';
      el.innerHTML = '<div style="height:100%;display:flex;align-items:center;justify-content:center;color:#9aa4b2;font-size:13px;text-align:center;line-height:1.8">图表库未能加载<br>请联网后刷新页面，数据与结论保持可用</div>';
    }
    return null;
  }
  if (!charts[key]) charts[key] = echarts.init(document.getElementById(id));
  return charts[key];
}

const f2 = (x) => (x === null || x === undefined || isNaN(x)) ? '--' : Number(x).toFixed(2);
const money = (x) => {
  if (x === null || x === undefined || isNaN(x)) return '--';
  if (Math.abs(x) >= 1e4) return (x / 1e4).toFixed(1) + ' 万';
  return x.toFixed(0);
};

function annVerdict(pct, val) {
  if (val < 0) return {cls:'p-bad', text:'期货升水，不利多头'};
  if (pct >= 70) return {cls:'p-ok', text:'贴水丰厚 · 历史高位'};
  if (pct >= 45) return {cls:'p-neutral', text:'贴水中性偏高'};
  if (pct >= 25) return {cls:'p-mid', text:'贴水中性偏低'};
  return {cls:'p-bad', text:'贴水偏薄 · 性价比低'};
}

function rollVerdict(pct, sig) {
  if (sig === 'roll') return {cls:'p-ok', text:'已进入换月窗口'};
  if (pct >= 55) return {cls:'p-neutral', text:'接近窗口，可开始盯'};
  return {cls:'p-mid', text:'未到窗口，继续持有'};
}

function buildBanner() {
  const d = DATA.products[CUR];
  if (!d) return '';
  const s = d.stats || {};
  const v = annVerdict(s.pct, s.current);
  const r = d.roll || {};
  let txt = '<b>' + CUR + ' ' + d.name_cn + '</b> 主力 ' + d.main +
    ' 年化贴水 <b>' + f2(s.current) + '%</b>，处于近一年 <b>' + f2(s.pct) + '%</b> 分位 —— ' + v.text + '。';
  if (r.near) {
    txt += '　近月−次月价差 <b>' + f2(r.spread) + '</b> 点（' + f2(r.pct) + '% 分位），' +
      (r.signal === 'roll' ? '<b>已到换月窗口</b>。' : '尚未到换月窗口。');
  }
  return txt;
}

function renderHeader() {
  document.getElementById('subline').textContent =
    '数据截止 ' + DATA.as_of + ' 收盘 · 四个品种 ｜ 表观年化贴水口径（未扣分红）';
  document.getElementById('stamp').innerHTML =
    '生成于<br>' + DATA.generated_at;
  document.getElementById('banner').innerHTML = buildBanner();
}

function renderTabs() {
  const box = document.getElementById('tabs');
  box.innerHTML = ORDER.map(p => {
    const d = DATA.products[p];
    if (!d) return '';
    const on = p === CUR ? ' on' : '';
    return '<div class="tab' + on + '" data-p="' + p + '">' + p + ' ' + d.name_cn + '</div>';
  }).join('');
  box.querySelectorAll('.tab').forEach(el => {
    el.onclick = () => { CUR = el.dataset.p; renderAll(); };
  });
}

function renderHead2() {
  const d = DATA.products[CUR];
  const s = d.stats || {};
  document.getElementById('mainAnn').innerHTML = f2(s.current) + '<small>%</small>';
  document.getElementById('mainMeta').innerHTML =
    '现货 <b>' + f2(d.spot) + '</b> ｜ 主力 <b>' + (d.main || '--') + '</b> ｜ 中位数 <b>' +
    f2(s.median) + '%</b> ｜ 样本 <b>' + (s.samples || 0) + '</b> 日';
  const v = annVerdict(s.pct, s.current);
  document.getElementById('annPill').innerHTML =
    '<span class="pill ' + v.cls + '">分位 ' + f2(s.pct) + '% · ' + v.text + '</span>';

  const r = d.roll || {};
  document.getElementById('rollPct').innerHTML = f2(r.pct) + '<small>%</small>';
  document.getElementById('rollMeta').innerHTML = r.near ?
    ('价差 <b>' + f2(r.spread) + '</b> 点 ｜ ' + r.near + ' → ' + r.far +
     ' ｜ 折合 <b>' + f2(r.per_month) + '</b> 点/月 ｜ 中位 <b>' + f2(r.median) + '</b>') : '暂无数据';
  const rv = rollVerdict(r.pct, r.signal);
  document.getElementById('rollPill').innerHTML =
    '<span class="pill ' + rv.cls + '">' + rv.text + '</span>';
}

function chartHist() {
  const d = DATA.products[CUR];
  const ser = d.main_series || {dates:[], annual:[]};
  const st = d.stats || {};
  const c1 = ensureChart('chartHist','hist');
  if (!c1) return;
  c1.setOption({
    grid:{left:44,right:16,top:26,bottom:34},
    tooltip:{trigger:'axis',valueFormatter:(v)=>f2(v)+'%'},
    xAxis:{type:'category',data:ser.dates,axisLine:{lineStyle:{color:'#dfe4ea'}},
      axisLabel:{color:'#8b95a3',fontSize:11,hideOverlap:true},axisTick:{show:false}},
    yAxis:{type:'value',axisLabel:{color:'#8b95a3',fontSize:11,formatter:'{value}%'},
      splitLine:{lineStyle:{color:'#eef1f5'}},axisLine:{show:false}},
    series:[{
      type:'line',data:ser.annual,smooth:false,showSymbol:false,
      lineStyle:{color:'#1f4e79',width:2},
      areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[
        {offset:0,color:'rgba(31,78,121,.18)'},{offset:1,color:'rgba(31,78,121,.01)'}]}},
      markLine:{silent:true,symbol:'none',
        label:{formatter:'中位 '+f2(st.median)+'%',color:'#d98207',fontSize:11,position:'insideEndTop'},
        lineStyle:{color:'#d98207',type:'dashed',width:1},
        data:[{yAxis:st.median}]},
      markPoint:{symbol:'circle',symbolSize:7,itemStyle:{color:'#cf2f2f'},
        label:{formatter:f2(st.current)+'%',color:'#cf2f2f',fontSize:11,position:'left'},
        data:[{coord:[ser.dates.length-1, st.current]}]}
    }]
  }, true);
}

function chartSlope() {
  const d = DATA.products[CUR];
  const ser = d.slope_series || [];
  const el = ensureChart('chartSlope','slope');
  if (!el) return;
  if (!ser.length) { el.clear(); return; }
  const monthly = ser.map((s,i)=>{
    const next = ser[i+1];
    return (!next || next.date.slice(0,7) !== s.date.slice(0,7)) ? s.slope : null;
  });
  const last = ser[ser.length-1];
  el.setOption({
    grid:{left:54,right:20,top:26,bottom:34},
    tooltip:{trigger:'axis',
      formatter:function(ps){
        const i = ps[0].dataIndex, s = ser[i];
        return s.date + '<br/>' + s.near + ' → ' + s.far + '（' + s.gap + ' 天）<br/>斜率 <b>' + f2(s.slope) + '%</b>';
      }},
    xAxis:{type:'category',data:ser.map(x=>x.date),axisLine:{lineStyle:{color:'#dfe4ea'}},
      axisLabel:{color:'#8b95a3',fontSize:11,hideOverlap:true},axisTick:{show:false}},
    yAxis:{type:'value',axisLabel:{color:'#8b95a3',fontSize:11,formatter:'{value}%'},
      splitLine:{lineStyle:{color:'#eef1f5'}},axisLine:{show:false},scale:true},
    series:[
      {name:'斜率',type:'line',data:ser.map(x=>x.slope),showSymbol:false,smooth:false,
       lineStyle:{color:'#7ba7cc',width:1.4},
       areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[
         {offset:0,color:'rgba(123,167,204,.22)'},{offset:1,color:'rgba(123,167,204,.02)'}]}},
       markLine:{silent:true,symbol:'none',label:{show:false},
         lineStyle:{color:'#c9d3de',type:'solid',width:1},data:[{yAxis:0}]}},
      {name:'月末',type:'line',data:monthly,symbol:'circle',symbolSize:6,
       lineStyle:{width:0},itemStyle:{color:'#1f4e79'},
       label:{show:true,position:'top',color:'#1f4e79',fontSize:10,formatter:function(p){return f2(p.value)+'%';}}}
    ]
  }, true);
}

function chartTerm() {
  const d = DATA.products[CUR];
  const cs = d.contracts || [];
  const c2 = ensureChart('chartTerm','term');
  if (!c2) return;
  c2.setOption({
    grid:{left:48,right:48,top:26,bottom:30},
    tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},
    legend:{data:['贴水点数','年化贴水'],right:0,top:0,itemWidth:10,itemHeight:8,textStyle:{fontSize:11,color:'#6b7684'}},
    xAxis:{type:'category',data:cs.map(c=>c.code),axisLine:{lineStyle:{color:'#dfe4ea'}},
      axisLabel:{color:'#8b95a3',fontSize:11},axisTick:{show:false}},
    yAxis:[
      {type:'value',name:'点',nameTextStyle:{color:'#8b95a3',fontSize:10},
        axisLabel:{color:'#8b95a3',fontSize:11},splitLine:{lineStyle:{color:'#eef1f5'}},axisLine:{show:false}},
      {type:'value',name:'%',nameTextStyle:{color:'#8b95a3',fontSize:10},
        axisLabel:{color:'#8b95a3',fontSize:11,formatter:'{value}%'},splitLine:{show:false},axisLine:{show:false}}
    ],
    series:[
      {name:'贴水点数',type:'bar',data:cs.map(c=>c.basis_pts),barWidth:'42%',
       itemStyle:{color:'#cf2f2f',borderRadius:[3,3,0,0]}},
      {name:'年化贴水',type:'line',yAxisIndex:1,data:cs.map(c=>c.annual_pct),
       symbol:'circle',symbolSize:6,lineStyle:{color:'#1f4e79',width:2},itemStyle:{color:'#1f4e79'}}
    ]
  }, true);
}

function chartContracts() {
  const d = DATA.products[CUR];
  const snaps = d.contract_snapshots || [];
  const el = ensureChart('chartContracts','contracts');
  if (!el) return;
  const labels = snaps.map(s => s.code.slice(2,4) + '/' + s.code.slice(4,6));
  el.setOption({
    grid:{left:48,right:16,top:28,bottom:40},
    tooltip:{trigger:'axis',axisPointer:{type:'shadow'},
      formatter: function(ps){
        const s = snaps[ps[0].dataIndex];
        return s.code + '　剩余 ' + s.days + ' 天<br/>' + s.date + '　年化 <b>' + f2(s.annual) + '%</b>';
      }},
    xAxis:{type:'category',data:labels,axisLine:{lineStyle:{color:'#dfe4ea'}},
      axisLabel:{color:'#8b95a3',fontSize:11,rotate:labels.length>10?40:0},axisTick:{show:false}},
    yAxis:{type:'value',axisLabel:{color:'#8b95a3',fontSize:11,formatter:'{value}%'},
      splitLine:{lineStyle:{color:'#eef1f5'}},axisLine:{show:false}},
    series:[{
      type:'bar',barWidth:'58%',
      data:snaps.map(s=>({value:s.annual,itemStyle:{color:s.code===d.main?'#cf2f2f':'#7ba7cc',borderRadius:[3,3,0,0]}})),
      markLine:{silent:true,symbol:'none',
        label:{formatter:'中位 '+f2((d.stats||{}).median)+'%',color:'#d98207',fontSize:11,position:'insideEndTop'},
        lineStyle:{color:'#d98207',type:'dashed',width:1},
        data:[{yAxis:(d.stats||{}).median}]}
    }]
  }, true);
}

function chartRoll() {
  const d = DATA.products[CUR];
  const ser = d.roll_series || {dates:[],spread:[]};
  const r = d.roll || {};
  const c3 = ensureChart('chartRoll','roll');
  if (!c3) return;
  const opt = {
    grid:{left:44,right:16,top:26,bottom:34},
    tooltip:{trigger:'axis',valueFormatter:(v)=>f2(v)+' 点'},
    xAxis:{type:'category',data:ser.dates,axisLine:{lineStyle:{color:'#dfe4ea'}},
      axisLabel:{color:'#8b95a3',fontSize:11,hideOverlap:true},axisTick:{show:false}},
    yAxis:{type:'value',axisLabel:{color:'#8b95a3',fontSize:11},
      splitLine:{lineStyle:{color:'#eef1f5'}},axisLine:{show:false}},
    series:[{
      type:'line',data:ser.spread,showSymbol:false,
      lineStyle:{color:'#3c7fb8',width:1.8},
      markLine:{silent:true,symbol:'none',
        label:{formatter:'当前 '+f2(r.spread),color:'#cf2f2f',fontSize:11,position:'insideEndTop'},
        lineStyle:{color:'#cf2f2f',type:'dashed',width:1},
        data:[{yAxis:r.spread}]}
    }]
  };
  c3.setOption(opt, true);
}

function renderCmp() {
  const rows = ORDER.filter(p=>DATA.products[p]).map(p=>{
    const d = DATA.products[p], s = d.stats || {}, r = d.roll || {};
    const cls = s.current >= 0 ? 'up' : 'down';
    return '<tr><td><b>' + p + '</b> <span class="muted">' + d.name_cn + '</span></td>' +
      '<td>' + f2(d.spot) + '</td>' +
      '<td class="' + cls + '"><b>' + f2(s.current) + '%</b></td>' +
      '<td>' + f2(s.median) + '%</td>' +
      '<td>' + f2(s.pct) + '%</td>' +
      '<td>' + f2(r.spread) + '</td>' +
      '<td>' + f2(r.pct) + '%</td></tr>';
  }).join('');
  document.getElementById('cmpTable').innerHTML =
    '<thead><tr><th>品种</th><th>现货</th><th>主力年化</th><th>近一年中位</th><th>年化分位</th><th>近−次月</th><th>价差分位</th></tr></thead><tbody>' +
    rows + '</tbody>';
}

function renderContracts() {
  const d = DATA.products[CUR];
  const cs = d.contracts || [];
  const mult = d.multiplier;
  const rows = cs.map(c=>{
    const nm = c.notional / 1e4;
    const mg = nm * 1e4 * (DATA.margin_rate);
    return '<tr><td><b>' + c.code + '</b></td>' +
      '<td>' + f2(c.close) + '</td>' +
      '<td>' + c.days + '</td>' +
      '<td class="' + (c.basis_pts>=0?'up':'down') + '">' + f2(c.basis_pts) + '</td>' +
      '<td>' + f2(c.annual_pct) + '%</td>' +
      '<td>' + nm.toFixed(1) + ' 万</td>' +
      '<td>' + (mg/1e4).toFixed(1) + ' 万</td>' +
      '<td>' + (c.oi/1e4).toFixed(2) + ' 万</td></tr>';
  }).join('');
  document.getElementById('ctTable').innerHTML =
    '<thead><tr><th>合约</th><th>收盘</th><th>剩余天数</th><th>贴水(点)</th><th>年化</th><th>名义价值</th><th>1手保证金</th><th>持仓量</th></tr></thead><tbody>' +
    rows + '</tbody>';
}

function calcPos() {
  const d = DATA.products[CUR];
  const mult = d.multiplier;
  const cur = (d.contracts.find(c=>c.code===d.main) || d.contracts[0] || {}).close || d.spot;
  const cap = parseFloat(document.getElementById('inCap').value) * 1e4;
  const lots = parseInt(document.getElementById('inLots').value, 10);
  const openEl = document.getElementById('inOpen');
  if (!openEl.dataset.touched) openEl.value = cur;
  const open = parseFloat(openEl.value);
  const mr = parseFloat(document.getElementById('inMargin').value) / 100;

  if (!cap || !lots || !open) return;
  const notional = lots * open * mult;
  const margin = notional * mr;
  const equity = cap + (cur - open) * mult * lots;
  const bufferPts = (equity - margin) / (mult * lots);
  const bufferPct = bufferPts / cur * 100;
  const usedPct = margin / cap * 100;
  const leverage = notional / cap;

  document.getElementById('oMargin').textContent = (margin/1e4).toFixed(1) + ' 万';
  document.getElementById('oUsed').textContent = usedPct.toFixed(1) + '%';
  document.getElementById('oLev').textContent = leverage.toFixed(2) + ' 倍';
  const bufEl = document.getElementById('oBuf');
  bufEl.textContent = bufferPts.toFixed(0) + ' 点';
  bufEl.className = 'v ' + (bufferPct > 10 ? 'down' : bufferPct > 3 ? '' : 'up');
  bufEl.style.color = bufferPct > 10 ? 'var(--down)' : bufferPct > 3 ? 'var(--warn)' : 'var(--up)';

  document.getElementById('calcNote').innerHTML =
    '按当前价 <b>' + f2(cur) + '</b> 计：名义价值 <b>' + (notional/1e4).toFixed(1) + ' 万</b>，' +
    '1 手保证金 <b>' + (margin/lots/1e4).toFixed(1) + ' 万</b>。' +
    '可承受指数再跌 <b>' + bufferPct.toFixed(1) + '%</b>（约 ' + bufferPts.toFixed(0) + ' 点）才触及追保。' +
    '保证金比例按 ' + (mr*100).toFixed(1) + '% 估算，实际以期货公司标准为准。';
}

function renderFoot() {
  document.getElementById('foot').innerHTML =
    '<b>口径说明</b><br>' +
    '1. 年化贴水 = (现货 − 期货) / 现货 × 365 / 剩余自然日。正值代表期货贴水，是多头可收取的收益垫。<br>' +
    '2. 本页为<b>表观贴水</b>（未扣成分股分红）。券商研报常用扣除分红后的净贴水口径，两者通常相差 1~2 个百分点，方向一致。<br>' +
    '3. 剩余天数按"合约月第三个周五"计算，未处理法定节假日顺延，对年化的影响小于 0.2 个百分点。<br>' +
    '4. 分位窗口为最近 244 个交易日；样本不足时按实际样本数计算，此时分位参考价值下降。<br>' +
    '5. 期货日行情来自中国金融期货交易所日统计，现货指数来自新浪财经。<br><br>' +
    '<b>免责声明</b>：以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。任何投资决策应结合个人风险承受能力、资金状况和投资目标独立判断，必要时咨询持牌专业机构。过往表现不预示未来收益。';
}

function renderAll() {
  renderTabs();
  renderHead2();
  chartHist();
  chartContracts();
  chartSlope();
  chartTerm();
  chartRoll();
  renderCmp();
  renderContracts();
  calcPos();
}

(function init() {
  renderHeader();
  renderFoot();
  renderAll();
  ['inCap','inLots','inOpen','inMargin'].forEach(id=>{
    const el = document.getElementById(id);
    el.addEventListener('input', ()=>{ if (id==='inOpen') el.dataset.touched='1'; calcPos(); });
  });
  window.addEventListener('resize', ()=>{
    Object.values(charts).forEach(c=>c.resize());
  });
})();
</script>
</body>
</html>
"""


def render(payload: dict) -> str:
    """Inject the metrics payload into the HTML template."""
    data_js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA_JSON__", data_js)
