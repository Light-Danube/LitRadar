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
    else if(url==='/api/annotation-adapters') data={formats:{json:true,ris:true},providers:[{id:'ollama',available:true,model:'fixture'}]};
    else if(url==='/api/summary') data={stats:{all:1},recent:[paper],reading_queue:[]};
    else if(url.startsWith('/api/papers?')) data={items:[paper],count:1};
    else if(url.includes('/annotations')||url.includes('/notes/history')) data={items:[],has_more:false};
    else if(url==='/api/papers/1') data={...paper,...(options.body?JSON.parse(options.body):{})};
    else if(url.startsWith('/api/graph')) data={nodes:[paper,{...paper,id:2,title:'Related paper'}],edges:[{source:'1',target:'2',type:'cites',provenance:[]}],seed_id:1,providers:['fixture']};
    else if(url.startsWith('/api/clusters?')) data={clusters:[]};
    else if(url==='/api/jobs') data={};
    else throw new Error('Unexpected fixture request: '+url);
    return {ok:true,json:async()=>data};
  };
  for(const file of ['theme.js','locales.js','graph-tools.js','graph-interactions.js','annotation-workflows.js','app.js']) w.eval(source('static/'+file));
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
test('wheel zoom anchors the cursor; dragging and keyboard moves persist geometry and reset cleanly',async t=>{
  const x=await workspace();t.after(()=>x.dom.window.close());
  x.key('3',{altKey:true});await settle();
  const svg=x.$('#graph-svg');svg.getBoundingClientRect=()=>({left:0,top:0,width:900,height:510});
  const before=svg.getAttribute('viewBox').split(' ').map(Number);
  const wheel=new x.w.WheelEvent('wheel',{clientX:200,clientY:150,deltaY:-150,bubbles:true,cancelable:true});
  svg.dispatchEvent(wheel);assert.ok(wheel.defaultPrevented);
  const after=svg.getAttribute('viewBox').split(' ').map(Number);
  assert.ok(after[2]<before[2]);assert.ok(Math.abs((200-after[0])/after[2]-200/900)<1e-8);
  const node=x.$('[data-node]'),circle=node.querySelector('circle'),count=x.requests.length;
  const edge=x.$('line[data-source]'),edgeStart=edge.getAttribute('x1');
  function pointer(type,target,clientX,clientY){
    // jsdom does not implement native PointerEvent dispatch; exercise the installed handlers.
    svg['on'+type]({type,target,button:0,pointerId:1,clientX,clientY});
  }
  pointer('pointerdown',circle,40,45);pointer('pointermove',svg,140,115);pointer('pointerup',svg,140,115);
  assert.match(node.getAttribute('transform'),/^translate\(/);assert.notEqual(edge.getAttribute('x1'),edgeStart);
  const key='litbeacon-graph-layout:synthetic:all';
  const saved=JSON.parse(x.w.localStorage.getItem(key));assert.ok(saved[1].x>40);
  node.dispatchEvent(new x.w.KeyboardEvent('keydown',{key:'ArrowRight',shiftKey:true,bubbles:true,cancelable:true}));
  assert.equal(JSON.parse(x.w.localStorage.getItem(key))[1].x,saved[1].x+20);
  assert.equal(x.requests.length,count);
  x.$('#graph-reset-layout').click();assert.deepEqual(JSON.parse(x.w.localStorage.getItem(key)),{});
  assert.equal(svg.getAttribute('viewBox'),'0 0 900 510');assert.equal(node.getAttribute('transform'),'translate(0 0)');
});
test('fresh inference is disabled without per-request consent and sends only the chosen provider/model after opt-in',async t=>{
  const x=await workspace();t.after(()=>x.dom.window.close());x.$('[data-paper]').click();await settle();
  assert.equal(x.$('#generate-annotation').disabled,true);
  assert.ok(!x.requests.some(r=>r.url.includes('/generate')));
  const consent=x.$('#llm-consent');consent.checked=true;consent.dispatchEvent(new x.w.Event('change'));
  assert.equal(x.$('#generate-annotation').disabled,false);
  x.$('#generate-annotation').click();await settle();
  const request=x.requests.find(r=>r.url.endsWith('/annotations/generate'));
  assert.deepEqual(JSON.parse(request.options.body),{provider:'ollama',model:'fixture',consent:true,language:'en'});
  assert.equal(consent.checked,false);assert.equal(x.$('#generate-annotation').disabled,true);
  consent.checked=true;consent.dispatchEvent(new x.w.Event('change'));
  x.$('#llm-model').value='another-model';x.$('#llm-model').dispatchEvent(new x.w.Event('input'));
  assert.equal(consent.checked,false);assert.equal(x.$('#generate-annotation').disabled,true);
});
test('multi-file import encodes synthetic files into one atomic request and retains unsaved notes',async t=>{
  const x=await workspace();t.after(()=>x.dom.window.close());x.$('[data-paper]').click();await settle();
  const notes=x.$('#detail-notes');notes.value='Unsaved';
  const input=x.$('#annotation-import');assert.equal(input.multiple,true);
  Object.defineProperty(input,'files',{value:[new x.w.File(['[{"content":"Synthetic"}]'],'notes.json'),new x.w.File(['TY  - JOUR\nTI  - Synthetic\nER  -\n'],'reference.ris')]});
  await input.onchange();await settle();
  const request=x.requests.find(r=>r.url.endsWith('/annotations/import-files'));
  const files=JSON.parse(request.options.body).files;assert.equal(files.length,2);
  assert.equal(files[1].format,'ris');assert.equal(Buffer.from(files[0].content_base64,'base64').toString(),'[{"content":"Synthetic"}]');
  assert.equal(x.$('#detail-notes'),notes);assert.equal(notes.value,'Unsaved');assert.equal(input.disabled,false);
});
test('annotation deletion and restoration send revision guards; cancellation makes no mutation',async t=>{
  const x=await workspace();t.after(()=>x.dom.window.close());x.$('[data-paper]').click();await settle();
  const list=x.$('#annotation-list');let confirm=false,calls=[],reloaded=0;
  const context={api:async(url,options)=>{calls.push({url,options});return {};},t:key=>key,esc:v=>String(v),confirm:()=>confirm,reload:async()=>{reloaded++;},onError:e=>{throw e;},clearEdit:()=>{}};
  const item={id:7,paper_id:1,revision:3,content:'Synthetic',deleted_at:null};
  function bind(value){list.innerHTML='<article data-annotation="7"><div class="detail-actions"><button data-edit>edit</button></div><div class="annotation-editor"></div></article>';x.w.AnnotationWorkflows.bindCards(list,[value],context);}
  bind(item);await list.querySelector('[data-recovery]').onclick();assert.equal(calls.length,0);
  confirm=true;await list.querySelector('[data-recovery]').onclick();
  assert.equal(calls[0].options.method,'DELETE');assert.deepEqual(JSON.parse(calls[0].options.body),{expected_revision:3});assert.equal(reloaded,1);
  bind({...item,revision:4,deleted_at:'synthetic timestamp'});assert.equal(list.querySelector('[data-edit]').hidden,true);
  await list.querySelector('[data-recovery]').onclick();assert.ok(calls[1].url.endsWith('/7/restore'));
  assert.equal(calls[1].options.method,'POST');assert.equal(JSON.parse(calls[1].options.body).expected_revision,4);
});
test('research-note restore confirms replacement and uses current provenance as the optimistic guard',async t=>{
  const x=await workspace();t.after(()=>x.dom.window.close());x.$('[data-paper]').click();await settle();
  const list=x.$('#history-list');list.innerHTML='<button data-restore-note="40" data-paper="1">Restore</button>';
  x.$('#note-provenance').dataset.noteId='50';let request=null,restored=null;
  x.w.AnnotationWorkflows.bindNoteHistory(list,{api:async(url,options)=>{request={url,options};return {id:1,notes:'Historical text'};},t:k=>k,confirm:()=>true,onRestored:value=>restored=value,onError:e=>{throw e;}});
  await list.querySelector('button').onclick();
  assert.equal(request.url,'/api/papers/1/notes/history/40/restore');assert.deepEqual(JSON.parse(request.options.body),{expected_note_id:50});
  assert.equal(restored.notes,'Historical text');
});
test('annotation version pagination retains the correct more control and restores a selected historical revision',async t=>{
  const x=await workspace();t.after(()=>x.dom.window.close());x.$('[data-paper]').click();await settle();
  const list=x.$('#annotation-list');list.innerHTML='<article data-annotation="7"><div class="detail-actions"></div><div class="annotation-editor"></div></article>';
  let calls=[],reloads=0;
  const context={api:async(url,options)=>{
    calls.push({url,options});if(options)return {};
    const later=url.includes('before_revision');return {items:(later?[2,1]:[4,3]).map(revision=>({revision,content:'Synthetic version',recorded_at:'fixture',deleted_at:null})),next_before_revision:later?null:3};
  },t:k=>k,esc:v=>String(v),confirm:()=>true,reload:async()=>{reloads++;},onError:e=>{throw e;},clearEdit:()=>{}};
  x.w.AnnotationWorkflows.bindCards(list,[{id:7,paper_id:1,revision:4,deleted_at:null}],context);
  const history=list.querySelector('details');history.open=true;history.ontoggle();await settle();
  const more=history.querySelector('.history-more');assert.equal(more.hidden,false);
  await more.onclick();assert.equal(more.hidden,true);assert.equal(history.querySelectorAll('[data-restore-revision]').length,4);
  await history.querySelector('[data-restore-revision="1"]').onclick();
  const restore=calls.find(r=>r.options);assert.deepEqual(JSON.parse(restore.options.body),{expected_revision:4,restore_revision:1});assert.equal(reloads,1);
});
