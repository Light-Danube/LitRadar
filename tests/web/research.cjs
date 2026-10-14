const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.resolve(__dirname,'../..');
const settle=async()=>{for(let i=0;i<18;i++)await new Promise(resolve=>setImmediate(resolve));};
function setup(t,locale){
  const dom=new JSDOM(fs.readFileSync(path.join(root,'web/index.html'),'utf8'),{url:'http://fixture.invalid',runScripts:'outside-only'});t.after(()=>dom.window.close());
  const w=dom.window,$=selector=>w.document.querySelector(selector),requests=[];
  w.localStorage.setItem('litbeacon-language',locale);w.matchMedia=()=>({matches:false,addEventListener(){}});w.confirm=()=>true;
  const papers=[{id:1,title:'Synthetic queued paper',venue:'Test Journal',status:'to-read',tags:[],authors:[],notes:'PRIVATE NOTES',abstract:'',relevance_score:0},{id:2,title:'<img src=x onerror=evil()>',venue:'Other',status:'new',tags:[],authors:[],notes:'',abstract:'',relevance_score:0}];
  let presets=[{id:1,revision:1,title:'<script>Topic</script>',icon:'chat',query:'context emotion',venue_query:'Synthetic journal',source_id:null,year_from:2023,year_to:2026}];
  const statement=value=>({value,origin:'unknown',source_ref:'',source_type:'',location:'',reviewed_at:'',recorded_at:'',verification_status:'unverified'});
  let worksheet={paper_id:1,revision:0,fields:{method:statement(''),task_scope:statement(''),author_limitations:statement(''),user_questions:statement(''),gap_candidate:statement(''),evidence_granularity:statement('metadata only'),verdict:statement(''),venue_type:statement('unknown'),publication_status:statement('unverified')}};
  let bundles=[];
  const mode={conflict:false,providerError:false,snapshotError:false};
  w.fetch=async(url,options={})=>{
    const method=options.method||'GET',body=options.body?JSON.parse(options.body):null;requests.push({url,method,body});const parsed=new URL(url,'http://fixture.invalid');let data;
    const artifact=(name,files)=>({identifier:name,relative_path:'research/'+name,files});
    if(parsed.pathname==='/api/health')data={database:'synthetic'};
    else if(parsed.pathname==='/api/summary')data={stats:{all:2},recent:papers,reading_queue:[papers[0]]};
    else if(parsed.pathname==='/api/papers')data={items:papers.filter(p=>parsed.searchParams.get('status')==='all'||p.status===parsed.searchParams.get('status')),count:2};
    else if(parsed.pathname==='/api/research/presets'&&method==='GET')data={items:presets};
    else if(parsed.pathname==='/api/research/presets'&&method==='POST'){data={...body,id:2,revision:1};presets.push(data);}
    else if(parsed.pathname.startsWith('/api/research/presets/')&&method==='PUT'){if(mode.presetConflict)return {ok:false,status:409,json:async()=>({detail:{status:'conflict',message:'Topic changed; reload before editing'}})};data={...body.fields,id:1,revision:2};presets[0]=data;}
    else if(parsed.pathname.startsWith('/api/research/presets/')&&method==='DELETE'){presets=presets.filter(p=>p.id!==Number(parsed.pathname.split('/').pop()));data={ok:true};}
    else if(parsed.pathname==='/api/research/artifacts')data={items:bundles};
    else if(parsed.pathname==='/api/research/venues/lookup')data={status:'ambiguous_venue',venues:[{source_id:'S1',display_name:'Synthetic journal',venue_type:'journal',issn_l:null,publisher:'Test Publisher'},{source_id:'S2',display_name:'Synthetic journal',venue_type:'conference/proceedings'}]};
    else if(parsed.pathname==='/api/research/search'){
      if(mode.providerError)return {ok:false,status:502,json:async()=>({detail:{status:'rate_limited',message:'Provider rate limited'}})};
      const saved=artifact(body.identifier||'search-test',['manifest.json','search.json']);bundles.unshift(saved);data={status:'ok',count:2,truncated:true,paper_ids:[2],papers:[papers[1]],artifact:saved};
    }
    else if(parsed.pathname.endsWith('/evidence')&&method==='GET')data=structuredClone(worksheet);
    else if(parsed.pathname.endsWith('/evidence')&&method==='PATCH'){
      if(mode.conflict)return {ok:false,status:409,json:async()=>({detail:{status:'conflict',message:'Evidence changed; reload before editing'}})};
      if(mode.snapshotError)return {ok:false,status:503,json:async()=>({detail:{status:'save_failed',saved_in_database:true,message:'Snapshot failed; reload database state before retrying'}})};
      worksheet={...worksheet,revision:worksheet.revision+1,fields:{...worksheet.fields,...body.fields}};const a=artifact('evidence-test',['manifest.json','evidence.json']);bundles.unshift(a);data={...worksheet,artifact:a};
    }
    else if(parsed.pathname==='/api/research/exports'){const a=artifact(body.identifier||'export-test',['manifest.json','matrix.md','matrix.csv']);bundles.unshift(a);data=a;}
    else throw new Error('Unexpected request '+method+' '+url);
    return {ok:true,json:async()=>structuredClone(data)};
  };
  for(const name of ['theme','locales','graph-tools','graph-interactions','annotation-workflows','research-workspace','app'])w.eval(fs.readFileSync(path.join(root,`web/static/${name}.js`),'utf8'));
  function input(selector,value){const el=$(selector);assert.ok(el,selector);el.value=value;el.dispatchEvent(new w.Event('input',{bubbles:true}));return el;}
  function submit(selector){$(selector).dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));}
  return {w,$,requests,input,submit,mode,remoteChange:()=>{worksheet.revision+=1;worksheet.fields.user_questions={...worksheet.fields.user_questions,value:'REMOTE question retained',origin:'user'};}};
}
for(const locale of ['en','uk'])test(`research desk explicit retrieval, escaped metadata, edits and saved downloads (${locale})`,async t=>{
  const {w,$,requests,input,submit}=setup(t,locale);await settle();
  assert.deepEqual([...w.document.querySelectorAll('[data-page]')].map(el=>el.dataset.page),['overview','inbox','graph','clusters','jobs','research']);
  w.document.dispatchEvent(new w.KeyboardEvent('keydown',{key:'6',altKey:true,bubbles:true}));await settle();
  assert.ok($('#rw-status'));assert.equal($('#rw-status').value,'to-read');assert.ok($('[data-select-paper="1"]'));assert.equal($('[data-select-paper="2"]'),null);
  assert.ok(!requests.some(r=>r.method==='POST'));assert.equal($('#rw-presets script'),null);
  $('[data-preset-apply="1"]').click();await settle();assert.equal($('#rw-query').value,'context emotion');assert.equal($('#rw-sourceId').value,'');assert.ok(!requests.some(r=>r.method==='POST'));
  submit('#rw-lookup-form');await settle();assert.equal(w.document.querySelectorAll('[data-choose-venue]').length,2);$('[data-choose-venue="S2"]').click();assert.equal($('#rw-sourceId').value,'S2');
  input('#rw-searchIdentifier','custom-search');submit('#rw-search-form');await settle();const search=requests.find(r=>r.url==='/api/research/search');assert.equal(search.body.source_id,'S2');assert.equal(search.body.year_from,2023);assert.equal(search.body.limit,20);assert.equal(search.body.identifier,'custom-search');assert.ok($('#rw-result-body').textContent.includes('<img'));assert.equal($('#rw-result-body img'),null);
  assert.ok($('#rw-artifacts a[href="/api/research/artifacts/custom-search/search.json"]'));
  $('#rw-status').value='new';$('#rw-status').dispatchEvent(new w.Event('change'));await settle();assert.ok($('#rw-library [data-select-paper="2"]'));
  const checked=$('#rw-library [data-select-paper="2"]');checked.checked=true;checked.dispatchEvent(new w.Event('change'));assert.equal($('#rw-export').disabled,false);
  $('[data-evidence-paper="2"]').click();await settle();assert.equal($('#rw-e-method').value,'');assert.equal($('#rw-e-evidence_granularity').value,'metadata only');
  input('#rw-e-method','Synthetic manual method');assert.equal($('#rw-e-method-origin').value,'user');input('#rw-e-method-source_ref','https://example.invalid/paper');input('#rw-e-method-location','Table 1');submit('#rw-evidence-form');await settle();
  const patch=requests.find(r=>r.method==='PATCH');assert.equal(patch.body.expected_revision,0);assert.deepEqual(Object.keys(patch.body.fields),['method']);assert.equal(patch.body.fields.method.origin,'user');assert.ok(!JSON.stringify(patch.body).includes('PRIVATE NOTES'));
  input('#rw-researchQuestion','Does selected context help?');input('#rw-exportIdentifier','comparison-one');submit('#rw-export-form');await settle();const exported=requests.find(r=>r.url==='/api/research/exports');assert.deepEqual(exported.body.paper_ids,[2]);assert.equal(exported.body.research_question,'Does selected context help?');assert.ok($('#rw-artifacts a[href="/api/research/artifacts/comparison-one/matrix.csv"]'));
  for(const control of w.document.querySelectorAll('#page-content input:not([type=checkbox]),#page-content textarea,#page-content select'))assert.ok(w.document.querySelector(`label[for="${control.id}"]`),'label '+control.id);
});
for(const locale of ['en','uk'])test(`research drafts survive locale/theme/navigation and conflict; topic CRUD (${locale})`,async t=>{
  const {w,$,requests,input,submit,mode,remoteChange}=setup(t,locale);await settle();$('[data-page=research]').click();await settle();
  input('#rw-query','Unsubmitted search');input('#rw-hypothesis','Unsubmitted hypothesis');$('[data-evidence-paper="1"]').click();await settle();input('#rw-e-method','Keep my method');input('#rw-e-method-location','Page 3');
  $('#language').value=locale==='en'?'uk':'en';$('#language').dispatchEvent(new w.Event('change'));await settle();assert.equal($('#rw-query').value,'Unsubmitted search');assert.equal($('#rw-e-method').value,'Keep my method');assert.equal($('#rw-e-method-location').value,'Page 3');
  $('#theme').value='dark';$('#theme').dispatchEvent(new w.Event('change'));assert.equal($('#rw-e-method').value,'Keep my method');
  $('[data-page=overview]').click();await settle();$('[data-page=research]').click();await settle();assert.equal($('#rw-hypothesis').value,'Unsubmitted hypothesis');assert.equal($('#rw-e-method').value,'Keep my method');
  mode.conflict=true;submit('#rw-evidence-form');await settle();assert.ok($('#rw-message').textContent.includes('reload'));assert.equal($('#rw-e-method').value,'Keep my method');assert.equal($('#rw-evidence-save').disabled,false);
  remoteChange();const patches=requests.filter(r=>r.method==='PATCH').length;$('#rw-evidence-reload').click();await settle();assert.equal(requests.filter(r=>r.method==='PATCH').length,patches);assert.equal($('#rw-e-method').value,'Keep my method');assert.equal($('#rw-e-user_questions').value,'REMOTE question retained');mode.conflict=false;submit('#rw-evidence-form');await settle();const retry=requests.filter(r=>r.method==='PATCH').at(-1);assert.deepEqual(Object.keys(retry.body.fields),['method']);assert.equal(retry.body.expected_revision,1);assert.ok($('#rw-artifacts a[href$="evidence.json"]'));
  $('[data-preset-edit="1"]').click();input('#rw-preset-title','Edited local topic');submit('#rw-preset-form');await settle();assert.equal(requests.find(r=>r.method==='PUT').body.expected_revision,1);
  $('#rw-new-preset').click();input('#rw-preset-title','New topic');input('#rw-preset-query','sarcasm context');input('#rw-preset-venue_query','Synthetic source');submit('#rw-preset-form');await settle();assert.ok(requests.find(r=>r.url==='/api/research/presets'&&r.method==='POST'));assert.equal($('#rw-preset-icon').value,'book');
  const posts=requests.filter(r=>r.url==='/api/research/presets'&&r.method==='POST').length;$('#rw-preset-delete').click();await settle();assert.equal(requests.filter(r=>r.url==='/api/research/presets'&&r.method==='POST').length,posts);assert.ok(requests.some(r=>r.method==='DELETE'));assert.equal($('[data-preset-apply="2"]'),null);
  assert.equal(requests.filter(r=>r.url.includes('/venues/lookup')||r.url==='/api/research/search').length,0);
});
test('provider failure reports structured status and retains search controls',async t=>{
  const {w,$,input,submit,mode}=setup(t,'en');await settle();$('[data-page=research]').click();await settle();input('#rw-sourceId','S1');input('#rw-query','Synthetic bounded search');mode.providerError=true;submit('#rw-search-form');await settle();assert.ok($('#rw-message').textContent.includes('Provider rate limited'));assert.ok(!$('#rw-message').textContent.includes('[object Object]'));assert.equal($('#rw-query').value,'Synthetic bounded search');assert.equal($('#rw-search').disabled,false);
});
test('slow evidence request cannot replace the latest selection',async t=>{
  const {w,$}=setup(t,'en');await settle();$('[data-page=research]').click();await settle();
  $('#rw-status').value='all';$('#rw-status').dispatchEvent(new w.Event('change'));await settle();
  const baseFetch=w.fetch;let release;
  w.fetch=(url,options)=>url==='/api/papers/1/evidence'&&(!options?.method||options.method==='GET')?new Promise(resolve=>{release=()=>baseFetch(url,options).then(resolve);}):baseFetch(url,options);
  $('[data-evidence-paper="1"]').click();$('[data-evidence-paper="2"]').click();await settle();assert.ok($('#rw-evidence h3').textContent.includes('#2'));release();await settle();assert.ok($('#rw-evidence h3').textContent.includes('#2'));
});
test('snapshot failure distinguishes saved database state and retains editor draft',async t=>{
  const {w,$,input,submit,mode}=setup(t,'en');await settle();$('[data-page=research]').click();await settle();$('[data-evidence-paper="1"]').click();await settle();input('#rw-e-method','Manual evidence');mode.snapshotError=true;submit('#rw-evidence-form');await settle();assert.ok($('#rw-message').textContent.includes('SQLite changes were saved'));assert.equal($('#rw-e-method').value,'Manual evidence');assert.equal($('#rw-evidence-save').disabled,false);
});
test('stale topic edit preserves user input instead of overwriting the newer preset',async t=>{
  const {w,$,input,submit,mode}=setup(t,'en');await settle();$('[data-page=research]').click();await settle();$('[data-preset-edit="1"]').click();input('#rw-preset-title','Unsaved topic change');mode.presetConflict=true;submit('#rw-preset-form');await settle();assert.equal($('#rw-preset-title').value,'Unsaved topic change');assert.ok($('#rw-message').textContent.includes('Another edit'));assert.equal($('#rw-preset-save').disabled,false);$('#rw-preset-reload').click();await settle();assert.equal($('#rw-preset-title').value,'Unsaved topic change');
});
test('typing while evidence save is pending survives response and locale navigation',async t=>{
  const {w,$,input,submit,requests}=setup(t,'en');await settle();$('[data-page=research]').click();await settle();$('[data-evidence-paper="1"]').click();await settle();
  const baseFetch=w.fetch;let release,delayNextPatch=true;
  w.fetch=async(url,options)=>{const response=await baseFetch(url,options);if(options?.method==='PATCH'&&delayNextPatch){delayNextPatch=false;return new Promise(resolve=>{release=()=>resolve(response);});}return response;};
  input('#rw-e-method','Submitted method');submit('#rw-evidence-form');await settle();assert.equal($('#rw-evidence-save').disabled,true);
  input('#rw-e-method','Edited during save');$('#language').value='uk';$('#language').dispatchEvent(new w.Event('change'));await settle();input('#rw-e-method','Latest text after locale change');release();await settle();
  assert.equal($('#rw-e-method').value,'Latest text after locale change');$('[data-page=overview]').click();await settle();$('[data-page=research]').click();await settle();assert.equal($('#rw-e-method').value,'Latest text after locale change');
  submit('#rw-evidence-form');await settle();const patches=requests.filter(r=>r.method==='PATCH');assert.equal(patches.length,2);assert.equal(patches[0].body.fields.method.value,'Submitted method');assert.equal(patches[1].body.fields.method.value,'Latest text after locale change');assert.equal(patches[1].body.expected_revision,1);
});
test('typing during revision reload survives together with newer untouched remote fields',async t=>{
  const {w,$,input,requests,submit,remoteChange}=setup(t,'en');await settle();$('[data-page=research]').click();await settle();$('[data-evidence-paper="1"]').click();await settle();
  const baseFetch=w.fetch;let release;
  w.fetch=(url,options)=>url==='/api/papers/1/evidence'&&(!options?.method||options.method==='GET')?new Promise(resolve=>{release=()=>baseFetch(url,options).then(resolve);}):baseFetch(url,options);
  input('#rw-e-method','Draft before reload');$('#rw-evidence-reload').click();await settle();input('#rw-e-method','Typed during reload');input('#rw-e-author_limitations','New local limitation');remoteChange();release();await settle();
  assert.equal($('#rw-e-method').value,'Typed during reload');assert.equal($('#rw-e-author_limitations').value,'New local limitation');assert.equal($('#rw-e-user_questions').value,'REMOTE question retained');submit('#rw-evidence-form');await settle();const patch=requests.find(r=>r.method==='PATCH');assert.deepEqual(Object.keys(patch.body.fields).sort(),['author_limitations','method']);assert.equal(patch.body.expected_revision,1);
});
