const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const root = path.resolve(__dirname, '../..');
const source = name => fs.readFileSync(path.join(root, 'web', name), 'utf8');
const settle = async () => { for (let i=0;i<12;i++) await new Promise(resolve=>setImmediate(resolve)); };
const paper = {id:1,title:'Synthetic study — Дослідження',authors:['Fixture'],abstract:'Synthetic evidence.',tags:[],notes:'',status:'new',relevance_score:.5};
async function workspace({stored, dark=false, blocked=false}={}) {
  const dom = new JSDOM(source('index.html'), {url:'http://fixture.invalid',runScripts:'outside-only'});
  const w = dom.window, requests=[];
  const media = new w.EventTarget(); media.matches=dark; w.matchMedia=()=>media;
  if(stored) w.localStorage.setItem('litbeacon-theme',stored);
  if(blocked) Object.defineProperty(w,'localStorage',{get(){throw new Error('Disabled storage');}});
  w.fetch=async (url,options={})=>{
    requests.push({url,options});
    let data;
    if(url==='/api/health') data={database:'synthetic'};
    else if(url==='/api/summary') data={stats:{all:1},recent:[paper],reading_queue:[]};
    else if(url.startsWith('/api/papers?')) data={items:[paper],count:1};
    else if(url.includes('/annotations')||url.includes('/notes/history')) data={items:[],has_more:false};
    else if(url==='/api/papers/1') data={...paper,...(options.body?JSON.parse(options.body):{})};
    else if(url.startsWith('/api/graph')) data={nodes:[paper],edges:[],seed_id:1,providers:[]};
    else if(url.startsWith('/api/clusters?')) data={clusters:[]};
    else if(url==='/api/jobs') data={};
    else throw new Error('Unexpected fixture request: '+url);
    return {ok:true,json:async()=>data};
  };
  for(const file of ['theme.js','locales.js','graph-tools.js','app.js']) w.eval(source('static/'+file));
  await settle();
  const change=(id,value)=>{const el=w.document.getElementById(id);el.value=value;el.dispatchEvent(new w.Event('change',{bubbles:true}));};
  const key=(key,options={})=>w.document.dispatchEvent(new w.KeyboardEvent('keydown',{key,bubbles:true,cancelable:true,...options}));
  return {dom,w,requests,media,change,key,$:selector=>w.document.querySelector(selector)};
}
test('theme initializes before CSS; system follows OS, explicit choices persist and ignore OS changes',async t=>{
  const html=source('index.html');assert.ok(html.indexOf('/static/theme.js')<html.indexOf('/static/styles.css'));
  const x=await workspace({dark:true});t.after(()=>x.dom.window.close());
  assert.equal(x.$('html').dataset.theme,'dark');assert.equal(x.$('#theme').value,'system');
  x.media.matches=false;x.media.dispatchEvent(new x.w.Event('change'));assert.equal(x.$('html').dataset.theme,'light');
  x.change('theme','dark');assert.equal(x.w.localStorage.getItem('litbeacon-theme'),'dark');
  x.media.dispatchEvent(new x.w.Event('change'));assert.equal(x.$('html').dataset.theme,'dark');
  x.change('theme','system');assert.equal(x.$('html').dataset.theme,'light');
});
test('stored, invalid and unavailable preferences all boot safely',async()=>{
  for(const [options,expected] of [[{stored:'light',dark:true},'light'],[{stored:'invalid',dark:true},'dark'],[{blocked:true},'light']]) {
    const x=await workspace(options);
    try {assert.equal(x.$('html').dataset.theme,expected);x.change('theme','dark');assert.equal(x.$('html').dataset.theme,'dark');assert.ok(x.$('[data-paper]'));}
    finally{x.dom.window.close();}
  }
});
test('theme changes preserve draft inputs, focus, selected paper and issue no API requests',async t=>{
  const x=await workspace();t.after(()=>x.dom.window.close());
  x.$('[data-paper]').click();await settle();
  const notes=x.$('#detail-notes');notes.value='Unsaved Ukrainian — нотатка';notes.focus();
  x.$('#annotation-content').value='Unsaved annotation';
  const count=x.requests.length;
  x.change('theme','dark');
  assert.equal(x.$('#detail-notes'),notes);assert.equal(x.w.document.activeElement,notes);
  assert.equal(notes.value,'Unsaved Ukrainian — нотатка');assert.equal(x.$('#annotation-content').value,'Unsaved annotation');
  assert.equal(x.requests.length,count);
});
test('locale switching retains drafts and theme; Ctrl+Enter saves the existing PATCH contract',async t=>{
  const x=await workspace();t.after(()=>x.dom.window.close());
  x.$('[data-paper]').click();await settle();
  x.$('#detail-notes').value='Чернетка';x.$('#detail-tags').value='synthetic, test';x.$('#detail-status').value='to-read';
  x.$('#annotation-content').value='Draft annotation';x.change('theme','dark');
  x.change('language','uk');await settle();
  assert.equal(x.$('html').lang,'uk');assert.equal(x.$('#theme-label').textContent,'Оформлення');
  assert.equal(x.$('#theme option[value=dark]').textContent,'Темне');assert.equal(x.$('#theme').value,'dark');
  assert.equal(x.$('#detail-notes').value,'Чернетка');assert.equal(x.$('#annotation-content').value,'Draft annotation');
  x.$('#detail-notes').focus();x.key('Enter',{ctrlKey:true});await settle();
  const patch=x.requests.find(r=>r.options.method==='PATCH');
  assert.equal(patch.url,'/api/papers/1');assert.deepEqual(JSON.parse(patch.options.body),{notes:'Чернетка',status:'to-read',tags:['synthetic','test']});
  x.change('language','en');await settle();assert.equal(x.$('#theme-label').textContent,'Appearance');
});
test('all five Alt shortcuts, search shortcut, graph keyboard selection and viewport survive themes',async t=>{
  const x=await workspace();t.after(()=>x.dom.window.close());
  for(const [index,page] of ['overview','inbox','graph','clusters','jobs'].entries()) {
    x.key(String(index+1),{altKey:true});await settle();
    assert.equal(x.$('[aria-current=page]').dataset.page,page);assert.equal(x.$('.error'),null,page);
  }
  x.$('#refresh').focus();x.key('/');await settle();assert.equal(x.w.document.activeElement.id,'paper-search');
  x.key('3',{altKey:true});await settle();
  const svg=x.$('#graph-svg'),node=x.$('[data-node]');
  node.dispatchEvent(new x.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
  assert.ok(node.classList.contains('selected'));
  svg.setAttribute('viewBox','10 20 450 255');x.change('theme','dark');
  assert.equal(x.$('#graph-svg'),svg);assert.equal(svg.getAttribute('viewBox'),'10 20 450 255');
  assert.ok(node.classList.contains('selected'));
});
