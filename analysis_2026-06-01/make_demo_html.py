import json
from pathlib import Path
D=Path(__file__).parent
data=Path(D/"data/demo_data.json").read_text()

html = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Funnel Intelligence — Demo</title>
<style>
 *{margin:0;padding:0;box-sizing:border-box}
 body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
   -webkit-font-smoothing:antialiased;background:#F5F5F5;color:#1A1A1A;padding:32px;max-width:920px;margin:0 auto}
 .grad{background:linear-gradient(90deg,#A855F7,#3B82F6,#06B6D4,#10B981,#F59E0B,#EF4444,#EC4899);
   -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
 .bar{height:5px;border-radius:3px;background:linear-gradient(90deg,#A855F7,#3B82F6,#06B6D4,#10B981,#F59E0B,#EF4444,#EC4899)}
 h1{font-size:30px;font-weight:800;letter-spacing:-.02em} .sub{color:#6B7280;margin:6px 0 26px;font-size:15px}
 select{font-size:16px;padding:12px 14px;border-radius:12px;border:1px solid #ddd;width:100%;background:#fff;margin-bottom:24px}
 .card{background:#fff;border-radius:18px;padding:24px 26px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:18px}
 .row{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}
 .niche{display:inline-block;background:#EDE4FB;color:#7C3AED;padding:5px 12px;border-radius:999px;font-size:13px;font-weight:600}
 .conf{display:inline-block;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:600;margin-left:8px}
 .conf.ok{background:#DCFCE7;color:#15803D} .conf.low{background:#FEF3C7;color:#92400E}
 .score{font-size:64px;font-weight:900;letter-spacing:-.03em;line-height:1}
 .muted{color:#6B7280;font-size:14px} .small{font-size:13px;color:#9CA3AF}
 .stats{display:flex;gap:26px;flex-wrap:wrap;margin-top:18px}
 .stat b{font-size:22px;font-weight:800;display:block} .stat span{font-size:12px;color:#9CA3AF}
 .rec{border-left:3px solid #10B981;padding:13px 16px;background:#FAFAFA;border-radius:10px;margin-bottom:10px}
 .rec.t{border-left-color:#F59E0B}
 .rec h3{font-size:15.5px;font-weight:700;margin-bottom:5px}
 .badge{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
   padding:2px 8px;border-radius:6px;margin-right:6px}
 .badge.u{background:#DBEAFE;color:#1D4ED8} .badge.n{background:#F3E8FF;color:#7E22CE}
 .badge.c{background:#FEF3C7;color:#92400E}
 .vs{font-size:12.5px;color:#9CA3AF}
 .caveat{font-size:12.5px;color:#92400E;background:#FEF3C7;border-radius:8px;padding:8px 11px;margin-top:8px}
 .sugg{margin-top:10px;border:1px solid #DBEAFE;border-radius:10px;padding:11px 13px;background:#F8FAFF}
 .suggh{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#1D4ED8;margin-bottom:7px}
 .suggcur{font-size:12px;color:#9CA3AF;margin-bottom:7px} .suggcur b{color:#6B7280;font-weight:600}
 .suggi{font-size:13.5px;color:#1A1A1A;background:#fff;border:1px solid #E5E7EB;border-radius:8px;padding:8px 11px;margin-bottom:6px}
 .suggn{font-size:11.5px;color:#6B7280;margin-top:4px;font-style:italic}
 .meterlabel{font-size:11px;color:#9CA3AF;letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px}
 .legend{font-size:12px;color:#9CA3AF;margin-top:10px}
 .tldr{margin-top:26px} .tldr summary{cursor:pointer;font-weight:700;font-size:15px}
 .tldr h4{font-size:13px;margin:14px 0 4px;color:#1A1A1A} .tldr p,.tldr li{font-size:13px;color:#4B5563;line-height:1.55}
 .tldr ol{margin:4px 0 0 18px} .tldr .k{color:#111;font-weight:600}
</style></head><body>
<div class="bar" style="width:60px;margin-bottom:18px"></div>
<h1>Funnel <span class="grad">Intelligence</span></h1>
<div class="sub">Pick a real funnel. The engine classifies its niche, scores it against that niche, and shows what the niche's winners do differently — separating experiments worth trying from changes our A/B data says to test, not apply.</div>
<select id="pick"></select>
<div id="out"></div>

<details class="tldr card">
  <summary>How this works <span style="color:#9CA3AF;font-weight:400">— 2-min methodology</span></summary>
  <p>We analysed <span class="k">~196,000 real Perspective funnels</span> (and ~10,000 historical A/B tests) to build three things:</p>
  <h4>1 · Niche</h4>
  <p>We embed every funnel's copy with a multilingual model and group them into 32 niches by meaning. A classifier assigns a new funnel to its niche from its text — <span class="k">92% agreement on funnels from accounts it never saw</span>, and it asks to confirm when unsure.</p>
  <h4>2 · Score (/100)</h4>
  <p>A model predicts a funnel's conversion <span class="k">percentile within its niche</span> from its design + copy. Validated honestly: <span class="k">&rho;=0.40 on unseen accounts</span> (it generalises, not memorises) and <span class="k">&rho;=0.48 predicting newer funnels from older ones</span> (predicts the future, not just fits the past).</p>
  <h4>3 · Recommendations</h4>
  <p>For each niche we measured what the best-converting funnels do differently. Suggestions are split into <span class="k">universal</span> moves, <span class="k">niche-specific</span> ones, and a <span class="k">&ldquo;test, don't apply&rdquo;</span> bucket — because some patterns (e.g. more form questions) correlate with winning but <em>cause</em> losses in real A/B tests.</p>
  <h4>The honest caveats</h4>
  <ol>
    <li>Funnel <span class="k">design explains ~13%</span> of conversion — audience, offer and traffic dominate. The score is a relative design-quality signal, not a CVR oracle.</li>
    <li>It's <span class="k">correlational</span>: recommendations are <span class="k">experiments to A/B-test</span>, not guaranteed fixes. The A/B flywheel turns the strong ones into confident, causal advice over time.</li>
    <li><span class="k">Copy is the biggest lever</span> (bigger than layout) — so the highest-value tests are usually messaging, which is why we also generate tailored opener suggestions.</li>
  </ol>
  <p style="margin-top:10px;color:#9CA3AF">Built by Alex + Claude. All on the real dataset, reproducible.</p>
</details>
<script>
const DATA = __DATA__;
const sel = document.getElementById('pick');
DATA.forEach((f,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${f.name}  —  ${f.niche}  (score ${f.score})`;sel.appendChild(o);});
function scoreColor(s){return s>=66?'#10B981':s>=33?'#F59E0B':'#EF4444';}
function render(f){
  const confCls = f.ask_user ? 'low' : 'ok';
  const confTxt = f.ask_user
     ? `niche ${f.conf}% — confirm? ${f.alt.map(a=>a.niche+' '+a.conf+'%').join(' / ')}`
     : `niche match ${f.conf}%`;
  let exp = f.exp.map(r=>`
    <div class="rec">
      <span class="badge ${r.universal?'u':'n'}">${r.universal?'universal':'niche-specific'}</span>
      <h3 style="display:inline">${r.text}</h3>
      <div class="vs">within-niche correlation ${r.corr>=0?'+':''}${r.corr}</div>
      ${r.suggestion?`<div class="sugg">
        <div class="suggh">✎ Try something like — generated from this funnel's content</div>
        ${r.suggestion.current?`<div class="suggcur">replaces your current opener: <b>${r.suggestion.current}</b></div>`:''}
        ${r.suggestion.try.map(t=>`<div class="suggi">${t}</div>`).join('')}
        <div class="suggn">A suggestion to A/B-test — generated from your funnel, not a guaranteed win.</div>
      </div>`:''}
    </div>`).join('');
  let test = f.test.map(r=>`
    <div class="rec t">
      <span class="badge c">test, don't apply</span>
      <h3 style="display:inline">${r.text}</h3>
      <div class="vs">strong correlation (${r.corr>=0?'+':''}${r.corr}) but adding form friction loses ~70–90% of A/B tests → run it as a test</div>
    </div>`).join('');
  let noteHtml = f.note ? `<div class="caveat" style="background:#EEF2FF;color:#3730A3">${f.note}</div>` : '';
  let expBlock = (exp || noteHtml) ? (exp + noteHtml)
       : '<div class="muted">This funnel already matches its niche\\'s winning profile on the features we measure.</div>';
  document.getElementById('out').innerHTML = `
    <div class="card">
      <div class="row">
        <div>
          <span class="niche">${f.niche}</span><span class="conf ${confCls}">${confTxt}</span>
          <div class="small" style="margin-top:8px">benchmarked against ${f.niche_n.toLocaleString()} funnels in this niche</div>
        </div>
        <div style="text-align:right">
          <div class="meterlabel">within-niche score</div>
          <div class="score" style="color:${scoreColor(f.score)}">${f.score}<span style="font-size:22px;color:#9CA3AF">/100</span></div>
        </div>
      </div>
      <div class="stats">
        <div class="stat"><b>${f.cvr}%</b><span>this funnel's CVR</span></div>
        <div class="stat"><b>${f.niche_median_cvr}%</b><span>niche median CVR</span></div>
        <div class="stat"><b>${f.visitors.toLocaleString()}</b><span>visitors</span></div>
        <div class="stat"><b>${f.stats.pages}</b><span>pages</span></div>
        <div class="stat"><b>${f.stats.form_qs}</b><span>form questions</span></div>
        <div class="stat"><b>${f.stats.opens_with_question?'Yes':'No'}</b><span>opens w/ question</span></div>
      </div>
    </div>
    <div class="card">
      <div class="meterlabel" style="margin-bottom:14px">Recommended experiments — funnels like yours that convert well tend to…</div>
      ${expBlock}
      ${test ? '<div class="meterlabel" style="margin:18px 0 12px">Test, don\\'t apply</div>'+test : ''}
      <div class="legend">Recommendations are correlational starting points (the niche's winners vs the rest), framed as experiments. The A/B flywheel turns the strong ones into confident, causal advice over time.</div>
    </div>`;
}
sel.addEventListener('change',()=>render(DATA[sel.value]));
render(DATA[0]);
</script></body></html>"""

Path(D/"demo.html").write_text(html.replace("__DATA__", data))
print("wrote demo.html")
