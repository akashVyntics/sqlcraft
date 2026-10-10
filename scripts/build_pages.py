"""Build a dependency-free, explicitly labelled GitHub Pages question-bank demo."""
import json
from pathlib import Path
from practice.questions import QUESTIONS

output = Path('docs')
output.mkdir(exist_ok=True)
payload = json.dumps(QUESTIONS, ensure_ascii=False).replace('<', '\\u003c')
html = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SQLCraft · SQL practice demo</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#0c1016;color:#e4e9f1}*{box-sizing:border-box}body{margin:0}header,main,footer{max-width:1160px;margin:auto;padding:24px}header{display:flex;justify-content:space-between;align-items:center;gap:16px}strong.logo{font-size:24px;color:#54dfac}a{color:#54dfac}h1{font-size:clamp(32px,5vw,58px);letter-spacing:-2px;margin:18px 0}p{line-height:1.7}.muted{color:#a6b2c3}.notice{background:#18241e;border:1px solid #335c48;padding:16px;border-radius:12px}.filters{display:flex;gap:12px;flex-wrap:wrap;margin:28px 0}select,input,button{font:inherit;border:1px solid #334052;border-radius:8px;background:#131c28;color:inherit;padding:12px}input{flex:1;min-width:180px}button{cursor:pointer}button:hover,button:focus-visible{border-color:#54dfac}.layout{display:grid;grid-template-columns:minmax(240px,1fr) minmax(0,2fr);gap:20px}#list{display:flex;flex-direction:column;gap:8px;max-height:720px;overflow:auto}#list button{text-align:left}#list button[aria-pressed=true]{background:#20372d;border-color:#54dfac}.tag{color:#54dfac;font-size:12px;display:block;margin-bottom:6px}article{border:1px solid #293445;background:#111923;border-radius:14px;padding:24px}h2{margin-top:0;font-size:26px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0c1016;padding:16px;border-radius:8px;line-height:1.65}details{margin:20px 0}summary{cursor:pointer;color:#54dfac}footer{font-size:13px;color:#a6b2c3}@media(max-width:760px){.layout{grid-template-columns:1fr}#list{max-height:270px}header,main,footer{padding:18px}article{padding:18px}}
</style></head><body>
<header><strong class="logo">SQLCraft<span style="color:#a6b2c3;font-size:14px"> / demo</span></strong><a href="https://github.com/akashVyntics/sqlcraft">Source code</a></header>
<main><p class="muted">SQL • BUSINESS ANALYTICS • DATA ENGINEERING</p><h1>Practice SQL.<br>Understand the business.</h1><p class="muted">24 original scenarios, from your first filter to production data pipelines. Read every question in English or Hinglish.</p>
<p class="notice"><strong>GitHub Pages demo.</strong> Explore questions, hints and solutions. SQL execution, sign-in and online progress require the separately hosted full application and are unavailable here.</p>
<div class="filters"><label>Language <select id="language"><option value="en">English</option><option value="hi">Hinglish</option></select></label><label>Level <select id="level"><option value="">All levels</option><option>Basic</option><option>Intermediate</option><option>Advanced</option><option>Engineering</option></select></label><input id="search" type="search" aria-label="Search questions" placeholder="Search questions or topics"></div>
<p id="count" class="muted" aria-live="polite"></p><div class="layout"><nav id="list" aria-label="SQL questions"></nav><article id="question" aria-label="Selected question"></article></div></main><footer>Free and open source. English + Hinglish. No account or personal data collected by this demo.</footer>
<script id="questions" type="application/json">PAYLOAD</script>
<script>
'use strict';
const questions=JSON.parse(document.getElementById('questions').textContent);
const byId=new Map(questions.map(q=>[q.id,q]));
let selected=byId.has(location.hash.slice(1))?location.hash.slice(1):questions[0].id;
const language=document.getElementById('language'),level=document.getElementById('level'),search=document.getElementById('search');
const element=(tag,text)=>{const e=document.createElement(tag);e.textContent=text;return e;};
function render(){
 const lang=language.value,term=search.value.trim().toLowerCase();
 const matches=questions.filter(q=>(!level.value||q.level===level.value)&&`${q.title.en} ${q.title.hi} ${q.topic} ${q.prompt.en} ${q.prompt.hi}`.toLowerCase().includes(term));
 document.getElementById('count').textContent=`${matches.length} questions`;
 if(!matches.some(q=>q.id===selected))selected=matches[0]?.id;
 const list=document.getElementById('list');list.replaceChildren();
 for(const q of matches){const button=element('button','');button.type='button';button.setAttribute('aria-pressed',String(q.id===selected));const tag=element('span',`${q.level} · ${q.topic}`);tag.className='tag';button.append(tag,element('span',q.title[lang]));button.onclick=()=>{selected=q.id;history.replaceState(null,'','#'+q.id);render();};list.append(button);}
 const panel=document.getElementById('question');panel.replaceChildren();const q=byId.get(selected);
 if(!q){panel.append(element('p',lang==='hi'?'Koi matching question nahi mila.':'No matching questions.'));return;}
 const tag=element('p',`${q.level} · ${q.topic}`);tag.className='tag';panel.append(tag,element('h2',q.title[lang]),element('p',q.prompt[lang]),element('p',`Tables: ${q.tables.join(', ')}`));
 for(const [title,text,isCode] of [[lang==='hi'?'Hint dekho':'Show hint',q.hint[lang],false],[lang==='hi'?'Solution aur explanation dekho':'Show solution and explanation',q.solution,true]]){const detail=element('details','');detail.append(element('summary',title),element(isCode?'pre':'p',text));if(isCode)detail.append(element('p',q.explanation[lang]));panel.append(detail);}
}
for(const control of [language,level,search])control.addEventListener('input',render);
window.addEventListener('hashchange',()=>{if(byId.has(location.hash.slice(1)))selected=location.hash.slice(1);render();});
render();
</script></body></html>'''.replace('PAYLOAD', payload)
(output / 'index.html').write_text(html, encoding='utf-8')
(output / '.nojekyll').touch()
print(f'Built Pages demo with {len(QUESTIONS)} bilingual questions in {output}')
