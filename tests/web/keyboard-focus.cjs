// Production DOM behavior only; jsdom does not establish native rendering or AT support.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.resolve(__dirname,'../..');
const source=name=>fs.readFileSync(path.join(root,'web',name),'utf8');
const settle=async()=>{for(let i=0;i<16;i++)await new Promise(resolve=>setImmediate(resolve));};

async function workspace(t,locale){
  const dom=new JSDOM(source('index.html'),{url:'http://fixture.invalid',runScripts:'outside-only'});
  t.after(()=>dom.window.close());
  const w=dom.window,$=selector=>w.document.querySelector(selector),requests=[];
  w.localStorage.setItem('litbeacon-language',locale);
  const media=new w.EventTarget();media.matches=false;w.matchMedia=()=>media;
  const paper={id:1,title:'Synthetic keyboard study — Дослідження',authors:['Fixture'],
    abstract:'Synthetic local evidence.',notes:'Saved paper note',tags:[],status:'new',relevance_score:.5};
  const annotations=[11,12].map(id=>({id,paper_id:1,kind:'user',origin_method:'declared',
    review_status:'unreviewed',revision:1,recorded_at:'synthetic timestamp',content:`Saved annotation ${id}`}));
  let gate=null;
  w.fetch=async(url,options={})=>{
    requests.push({url,options});
    assert.equal(options.method||'GET','GET','Focus/cancellation must not mutate the API');
    const parsed=new URL(url,'http://fixture.invalid');let data;
    if(parsed.pathname==='/api/health')data={database:'synthetic-keyboard'};
    else if(parsed.pathname==='/api/summary')data={stats:{all:1},recent:[paper],reading_queue:[]};
    else if(parsed.pathname==='/api/papers')data={items:[paper],count:1};
    else if(parsed.pathname==='/api/papers/1')data={...paper};
    else if(parsed.pathname==='/api/papers/1/annotations'){
      if(gate){const pending=gate;gate=null;await pending;}
      data={items:annotations.map(item=>({...item})),has_more:false,note_provenance:null};
    }else if(parsed.pathname.includes('/notes/history'))data={items:[],has_more:false};
    else if(parsed.pathname==='/api/annotation-adapters')data={formats:{json:true,ris:true},providers:[]};
    else throw Error('Unexpected fixture request '+url);
    return {ok:true,json:async()=>data};
  };
  for(const name of ['theme.js','locales.js','graph-tools.js','graph-interactions.js','annotation-workflows.js','app.js'])w.eval(source('static/'+name));
  await settle();$('[data-paper="1"]').click();await settle();
  assert.equal(w.document.documentElement.lang,locale);
  const input=(selector,value)=>{const element=$(selector);element.value=value;element.dispatchEvent(new w.Event('input',{bubbles:true}));return element;};
  const key=(element,options={})=>{const event=new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true,...options});element.dispatchEvent(event);return event;};
  const assertNoWrites=()=>assert.equal(requests.filter(request=>(request.options.method||'GET')!=='GET').length,0);
  return {w,$,input,key,assertNoWrites,holdAnnotations(){let release;gate=new Promise(resolve=>{release=resolve;});return release;}};
}

function independentDrafts(x){
  x.input('#detail-notes','Unsaved paper note — нотатка');
  x.input('#annotation-content','Unsaved new annotation — чернетка');
  x.input('#annotation-source','Synthetic unsaved provenance');
}

function assertIndependentDrafts(x){
  assert.equal(x.$('#detail-notes').value,'Unsaved paper note — нотатка');
  assert.equal(x.$('#annotation-content').value,'Unsaved new annotation — чернетка');
  assert.equal(x.$('#annotation-source').value,'Synthetic unsaved provenance');
  assert.equal(x.$('#edit-12').value,'Other inline edit stays');
}

for(const locale of ['en','uk']){
  test(`explicit Edit and Cancel return focus without losing other drafts (${locale})`,async t=>{
    const x=await workspace(t,locale);
    const edit=x.$('[data-edit="11"]');edit.focus();edit.click();
    assert.equal(x.w.document.activeElement?.id,'edit-11','Explicit Edit must focus its textarea');
    x.input('#edit-11','Current edit is discarded');
    x.$('[data-edit="12"]').click();x.input('#edit-12','Other inline edit stays');independentDrafts(x);
    const cancel=x.$('[data-annotation="11"] [data-cancel]');cancel.focus();cancel.click();
    assert.equal(Boolean(x.$('#edit-11')),false);
    assert.equal(x.w.document.activeElement?.dataset.edit,'11','Cancel must return focus to the corresponding Edit button');
    assertIndependentDrafts(x);
    edit.click();assert.equal(x.$('#edit-11').value,'Saved annotation 11','Cancelled content must not reappear');
    assert.equal(x.w.document.activeElement?.id,'edit-11');
    x.assertNoWrites();
  });

  test(`Escape cancels only its editor and ignores IME composition (${locale})`,async t=>{
    const x=await workspace(t,locale);
    x.$('[data-edit="11"]').click();x.input('#edit-11','Current inline draft');
    x.$('[data-edit="12"]').click();x.input('#edit-12','Other inline edit stays');independentDrafts(x);
    const editor=x.$('#edit-11');editor.focus();
    const composing=x.key(editor,{isComposing:true});
    assert.equal(composing.defaultPrevented,false);
    assert.equal(x.$('#edit-11')===editor,true);assert.equal(editor.value,'Current inline draft');
    const save=x.$('[data-annotation="11"] [data-save]');save.focus();
    const escape=x.key(save);
    assert.equal(escape.defaultPrevented,true,'Escape from a control inside the editor must be handled');
    assert.equal(Boolean(x.$('#edit-11')),false);
    assert.equal(x.w.document.activeElement?.dataset.edit,'11');
    assertIndependentDrafts(x);
    const unrelated=x.$('#annotation-content');unrelated.focus();
    assert.equal(x.key(unrelated).defaultPrevented,false);
    assertIndependentDrafts(x);
    x.$('[data-edit="11"]').click();assert.equal(x.$('#edit-11').value,'Saved annotation 11');
    x.assertNoWrites();
  });

  test(`locale and navigation restore inline drafts without stealing focus (${locale})`,async t=>{
    const x=await workspace(t,locale);
    x.$('[data-edit="11"]').click();x.input('#edit-11','Restored first inline draft');
    x.$('[data-edit="12"]').click();x.input('#edit-12','Other inline edit stays');independentDrafts(x);
    const language=x.$('#language'),release=x.holdAnnotations();language.focus();
    language.value=locale==='en'?'uk':'en';language.dispatchEvent(new x.w.Event('change'));await settle();
    assert.equal(x.w.document.activeElement?.id,'language','Locale rendering must preserve header focus');
    const notes=x.$('#detail-notes');notes.focus();release();await settle();
    assert.equal(x.w.document.activeElement===notes,true,'Delayed annotation restoration must preserve another field focus');
    assert.equal(x.$('#edit-11').value,'Restored first inline draft');assertIndependentDrafts(x);
    const overview=x.$('[data-page="overview"]');overview.focus();overview.click();await settle();
    assert.equal(x.w.document.activeElement?.dataset.page,'overview');
    const inbox=x.$('[data-page="inbox"]');inbox.focus();inbox.click();await settle();
    assert.equal(x.w.document.activeElement?.dataset.page,'inbox','Navigation rehydration must not focus an inline editor');
    assert.equal(x.$('#edit-11').value,'Restored first inline draft');assertIndependentDrafts(x);
    language.focus();language.value=locale;language.dispatchEvent(new x.w.Event('change'));await settle();
    assert.equal(x.w.document.activeElement?.id,'language');assert.equal(x.w.document.documentElement.lang,locale);
    assert.equal(x.$('#edit-11').value,'Restored first inline draft');assertIndependentDrafts(x);
    assert.equal(Boolean(x.$('.error')),false);x.assertNoWrites();
  });
}
