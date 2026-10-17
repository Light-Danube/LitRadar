// DOM focus/handlers only: explicit click models browser Enter/Space defaults.
// jsdom cannot establish native Tab order, real keyboard activation or downloads.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.resolve(__dirname,'../..');
const settle=async()=>{for(let i=0;i<18;i++)await new Promise(resolve=>setImmediate(resolve));};

function workspace(t,locale){
  const dom=new JSDOM(fs.readFileSync(path.join(root,'web/index.html'),'utf8'),{url:'http://fixture.invalid',runScripts:'outside-only'});
  t.after(()=>dom.window.close());
  const w=dom.window,$=selector=>w.document.querySelector(selector),requests=[];
  w.localStorage.setItem('litbeacon-language',locale);
  w.matchMedia=()=>({matches:false,addEventListener(){}});w.confirm=()=>true;
  const paper={id:1,title:'Synthetic context study — Дослідження',authors:['Fixture'],
    status:'to-read',venue:'Synthetic Journal',tags:[],notes:'PRIVATE_NOTE_NOT_FOR_REQUESTS',abstract:'Synthetic only',relevance_score:.5};
  const other={...paper,id:2,title:'Second synthetic study'};
  const statement=value=>({value,origin:'unknown',source_ref:'',source_type:'',location:'',reviewed_at:'',recorded_at:'',verification_status:'unverified'});
  const worksheets=Object.fromEntries([1,2].map(id=>[id,{paper_id:id,revision:0,
    fields:{task_scope:statement(''),method:statement(''),author_limitations:statement('')}}]));
  const bundles=[];
  const artifact=(identifier,files)=>({identifier,relative_path:'research/'+identifier,files});
  w.fetch=async(url,options={})=>{
    assert.ok(url.startsWith('/api/'),'Only the synthetic local API may be used');
    const method=options.method||'GET',body=options.body?JSON.parse(options.body):null;
    requests.push({url,method,body});
    const parsed=new URL(url,'http://fixture.invalid');let data;
    const evidenceId=parsed.pathname.match(/^\/api\/papers\/(\d+)\/evidence$/)?.[1];
    if(parsed.pathname==='/api/health')data={database:'synthetic'};
    else if(parsed.pathname==='/api/summary')data={stats:{all:2},recent:[paper,other],reading_queue:[paper]};
    else if(parsed.pathname==='/api/papers')data={items:[paper,other],count:2};
    else if(parsed.pathname==='/api/research/presets')data={items:[]};
    else if(parsed.pathname==='/api/research/artifacts')data={items:bundles};
    else if(parsed.pathname==='/api/research/venues/lookup')data={status:'ambiguous_venue',venues:[
      {source_id:'S101',display_name:'Synthetic Journal',venue_type:'journal',publisher:'Fixture'},
      {source_id:'S202',display_name:'Synthetic Proceedings',venue_type:'conference/proceedings',publisher:'Fixture'}]};
    else if(parsed.pathname==='/api/research/search'){
      const saved=artifact(body.identifier,['manifest.json','search.json']);bundles.unshift(saved);
      data={status:'ok',count:1,truncated:false,paper_ids:[1],papers:[paper],artifact:saved};
    }else if(evidenceId&&method==='GET')data=worksheets[evidenceId];
    else if(evidenceId&&method==='PATCH'){
      let worksheet=worksheets[evidenceId];
      assert.equal(body.expected_revision,worksheet.revision);
      worksheet={...worksheet,revision:worksheet.revision+1,fields:{...worksheet.fields,...body.fields}};
      worksheets[evidenceId]=worksheet;
      const saved=artifact('synthetic-evidence',['manifest.json','evidence.json']);bundles.unshift(saved);
      data={...worksheet,artifact:saved};
    }else if(parsed.pathname==='/api/research/exports'){
      data=artifact(body.identifier,['manifest.json','matrix.md','matrix.csv']);bundles.unshift(data);
    }else throw Error('Unexpected synthetic request '+method+' '+url);
    return {ok:true,json:async()=>structuredClone(data)};
  };
  for(const name of ['theme','locales','graph-tools','graph-interactions','annotation-workflows','research-workspace','app'])
    w.eval(fs.readFileSync(path.join(root,`web/static/${name}.js`),'utf8'));
  function activate(element,key='Enter'){
    assert.ok(element,'Activation target exists');element.focus();
    assert.equal(w.document.activeElement,element,'The control is focusable');
    const allowed=element.dispatchEvent(new w.KeyboardEvent('keydown',{key,bubbles:true,cancelable:true}));
    if(allowed)element.click(); // Explicit model of the browser's default action.
    element.dispatchEvent(new w.KeyboardEvent('keyup',{key,bubbles:true}));
  }
  function input(selector,value){const element=$(selector);element.focus();element.value=value;element.dispatchEvent(new w.Event('input',{bubbles:true}));return element;}
  return {w,$,requests,activate,input};
}

for(const locale of ['en','uk'])test(`Research discovery, evidence and saved-export focus journey (${locale})`,async t=>{
  const {w,$,requests,activate,input}=workspace(t,locale),focusFailures=[];
  const expectFocus=(selector,step)=>{
    const expected=$(selector),actual=w.document.activeElement;
    assert.ok(expected,'Expected target exists: '+selector);
    if(actual!==expected)focusFailures.push(`${step}: expected ${selector}; actual ${actual?.id||actual?.tagName}`);
  };
  const translated=key=>w.LitI18n.translate(locale,key);
  await settle();
  const nav=$('[data-page="research"]');
  assert.ok(nav.textContent.includes(translated('research')));
  activate(nav);await settle();expectFocus('#rw-venueQuery','explicit Research navigation');
  assert.equal(w.document.documentElement.lang,locale);
  assert.equal(requests.filter(request=>request.method!=='GET').length,0,'Navigation makes no provider request');
  input('#rw-venueQuery','Synthetic venue');
  assert.equal($('#rw-lookup').textContent,translated('rw_lookup'));
  activate($('#rw-lookup'));await settle();expectFocus('[data-choose-venue="S101"]','venue lookup choices');
  assert.equal(w.document.querySelectorAll('[data-choose-venue]').length,2);
  activate($('[data-choose-venue="S101"]'));expectFocus('#rw-query','venue choice');
  assert.equal($('#rw-sourceId').value,'S101');
  assert.equal(requests.filter(request=>request.url==='/api/research/search').length,0,'Choosing a venue does not search');
  input('#rw-query','Synthetic context');input('#rw-searchIdentifier','keyboard-search');
  activate($('#rw-search'));await settle();expectFocus('#rw-result-papers [data-select-paper="1"]','search results');
  const search=requests.find(request=>request.url==='/api/research/search');
  assert.equal(search.body.source_id,'S101');assert.equal(search.body.query,'Synthetic context');
  assert.equal($('#rw-result-papers').textContent.includes('Synthetic context study'),true);
  activate($('#rw-result-papers [data-select-paper="1"]'),' ');
  assert.equal($('#rw-export').disabled,false);
  const evidence=$('#rw-result-papers [data-evidence-paper="1"]');
  assert.equal(evidence.textContent,translated('rw_editEvidence'));
  activate(evidence);await settle();expectFocus('#rw-e-task_scope','explicit evidence editor');
  input('#rw-e-task_scope','Synthetic reviewed scope — контекст');
  activate($('#rw-evidence-save'));await settle();expectFocus('#rw-evidence-save','evidence save replacement');
  const saved=requests.find(request=>request.method==='PATCH');
  assert.deepEqual(Object.keys(saved.body.fields),['task_scope']);assert.equal(saved.body.expected_revision,0);
  assert.equal(saved.body.fields.task_scope.origin,'user');
  assert.equal($('#rw-e-task_scope').value,'Synthetic reviewed scope — контекст');
  const writesBeforeReload=requests.filter(request=>request.method==='PATCH').length;
  activate($('#rw-evidence-reload'));await settle();expectFocus('#rw-evidence-reload','evidence reload replacement');
  assert.equal(requests.filter(request=>request.method==='PATCH').length,writesBeforeReload,'Reload never saves implicitly');
  assert.equal($('#rw-e-task_scope').value,'Synthetic reviewed scope — контекст');
  input('#rw-exportIdentifier','keyboard-export');input('#rw-researchQuestion','Synthetic research question');
  activate($('#rw-export'));await settle();
  const link='#rw-artifacts a[href="/api/research/artifacts/keyboard-export/matrix.md"]';
  expectFocus(link,'new saved export download');
  const exported=requests.find(request=>request.url==='/api/research/exports');
  assert.deepEqual(exported.body.paper_ids,[1]);assert.equal(exported.body.research_question,'Synthetic research question');
  assert.ok($(link).hasAttribute('download'));
  let activatedDownload=null;
  $(link).addEventListener('click',event=>{event.preventDefault();activatedDownload=event.currentTarget.getAttribute('href');},{once:true});
  activate($(link));assert.equal(activatedDownload,'/api/research/artifacts/keyboard-export/matrix.md');
  assert.ok(requests.every(request=>!JSON.stringify(request.body).includes('PRIVATE_NOTE_NOT_FOR_REQUESTS')));
  assert.equal(requests.filter(request=>request.method==='POST').length,3,'Only explicit lookup/search/export request actions');
  assert.deepEqual(focusFailures,[],'Research keyboard journey focus handoffs');
});

test('late lookup and locale rendering preserve a newer field/header focus',async t=>{
  const {w,$,requests,activate,input}=workspace(t,'en');await settle();
  activate($('[data-page="research"]'));await settle();input('#rw-venueQuery','Synthetic venue');
  const baseFetch=w.fetch;let release;
  w.fetch=(url,options)=>url==='/api/research/venues/lookup'?new Promise(resolve=>{
    release=()=>baseFetch(url,options).then(resolve);
  }):baseFetch(url,options);
  activate($('#rw-lookup'));await settle();
  const newer=input('#rw-query','New unsent query typed while lookup is pending');
  release();await settle();
  assert.equal(w.document.activeElement,newer,'A late response must not replace a newer user focus');
  assert.equal($('#rw-query').value,'New unsent query typed while lookup is pending');
  assert.equal(w.document.querySelectorAll('[data-choose-venue]').length,2);
  const language=$('#language');language.focus();language.value='uk';language.dispatchEvent(new w.Event('change'));await settle();
  assert.equal(w.document.activeElement,language,'Automatic locale rendering must not focus the first Research field');
  assert.equal($('#rw-query').value,'New unsent query typed while lookup is pending');
  assert.equal(requests.filter(request=>request.method!=='GET').length,1,'Only explicit venue lookup was requested');
});

test('pending evidence saves retain the active expanded field and never rebuild a different paper editor',async t=>{
  const {w,$,activate,input}=workspace(t,'en'),failures=[];await settle();
  activate($('[data-page="research"]'));await settle();
  activate($('#rw-library [data-evidence-paper="1"]'));await settle();
  const baseFetch=w.fetch;let release;
  w.fetch=async(url,options)=>{
    const response=await baseFetch(url,options);
    return options?.method==='PATCH'?new Promise(resolve=>{release=()=>resolve(response);}):response;
  };
  $('#rw-e-author_limitations').closest('details.research-field-group').open=true;
  input('#rw-e-author_limitations','Submitted assessment');activate($('#rw-evidence-save'));await settle();
  input('#rw-e-author_limitations','New assessment typed while saving');
  release();await settle();
  assert.equal($('#rw-e-author_limitations').value,'New assessment typed while saving');
  if(!$('#rw-e-author_limitations').closest('details.research-field-group').open)failures.push('Assessment group closed after pending save');
  if(w.document.activeElement!==$('#rw-e-author_limitations'))failures.push('Assessment textarea lost newer input focus');
  activate($('#rw-evidence-save'));await settle();
  activate($('#rw-library [data-evidence-paper="2"]'));await settle();
  const current=input('#rw-e-task_scope','Unsaved second-paper scope');
  release();await settle();
  assert.ok($('#rw-evidence h3').textContent.includes('#2'));
  assert.equal($('#rw-e-task_scope').value,'Unsaved second-paper scope');
  if($('#rw-e-task_scope')!==current)failures.push('Saving paper 1 rebuilt the paper 2 editor');
  if(w.document.activeElement!==current)failures.push('Saving paper 1 changed focus in paper 2');
  assert.deepEqual(failures,[],'Pending-save context must preserve the active editor');
});
