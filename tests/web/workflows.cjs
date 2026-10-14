// DOM workflow smoke tests run the production scripts; no external requests.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.resolve(__dirname,'../..');
const source=name=>fs.readFileSync(path.join(root,'web',name),'utf8');
const settle=async()=>{for(let i=0;i<16;i++)await new Promise(resolve=>setImmediate(resolve));};

for(const locale of ['en','uk']) test(`inbox editing → cluster paper → seeded graph → detail roundtrip (${locale})`,async t=>{
  const dom=new JSDOM(source('index.html'),{url:'http://fixture.invalid',runScripts:'outside-only'});
  t.after(()=>dom.window.close());const w=dom.window,$=s=>w.document.querySelector(s),requests=[];
  w.localStorage.setItem('litbeacon-language',locale);
  const media=new w.EventTarget();media.matches=false;w.matchMedia=()=>media;
  const papers=[{id:1,title:'Synthetic seed — Дослідження',authors:['Fixture'],abstract:'Synthetic context.',notes:'',tags:[],status:'new',relevance_score:.5},
    {id:2,title:'Synthetic reference',authors:[],abstract:'Synthetic prior.',notes:'',tags:['shared'],status:'new',relevance_score:.4}];
  w.fetch=async(url,options={})=>{
    requests.push({url,options});const parsed=new URL(url,'http://fixture.invalid');let data;
    if(parsed.pathname==='/api/health')data={database:'synthetic-workflow'};
    else if(parsed.pathname==='/api/summary')data={stats:{all:2},recent:papers,reading_queue:[]};
    else if(parsed.pathname==='/api/papers'){
      const q=parsed.searchParams.get('q')||'',status=parsed.searchParams.get('status');
      const items=papers.filter(p=>p.title.includes(q)&&(!status||status==='all'||p.status===status));data={items,count:items.length};
    }else if(/^\/api\/papers\/\d+$/.test(parsed.pathname)){
      const p=papers.find(p=>p.id===Number(parsed.pathname.split('/').pop()));
      if(options.method==='PATCH')Object.assign(p,JSON.parse(options.body));data={...p};
    }else if(parsed.pathname.includes('/annotations')||parsed.pathname.includes('/notes/history'))data={items:[],has_more:false};
    else if(parsed.pathname==='/api/annotation-adapters')data={formats:{json:true,ris:true},providers:[]};
    else if(parsed.pathname==='/api/clusters')data={method:'heuristic',clusters:[{label:'Tag · shared',size:2,papers}]};
    else if(parsed.pathname==='/api/graph')data={nodes:papers,seed_id:Number(parsed.searchParams.get('seed_id')),providers:['openalex','semantic_scholar'],edges:[{source:'1',target:'2',type:'cites',providers:['openalex','semantic_scholar'],provenance:[{provider:'openalex',observed_at:'fixture'},{provider:'semantic_scholar',observed_at:'fixture'}]}]};
    else throw Error('Unexpected request '+url);
    return {ok:true,json:async()=>data};
  };
  for(const file of ['theme.js','locales.js','graph-tools.js','graph-interactions.js','annotation-workflows.js','app.js'])w.eval(source('static/'+file));
  await settle();
  // Locales must use the app's existing setting path, regardless of storage key.
  const language=$('#language');language.value=locale;language.dispatchEvent(new w.Event('change'));await settle();
  $('[data-page=inbox]').click();await settle();
  $('[data-paper="1"]').click();await settle();
  $('#detail-notes').value='Saved — збережено';$('#detail-tags').value='shared, synthetic';$('#detail-status').value='to-read';
  $('#save-annotation').click();await settle();
  assert.deepEqual(JSON.parse(requests.find(r=>r.options.method==='PATCH').options.body),{notes:'Saved — збережено',tags:['shared','synthetic'],status:'to-read'});
  $('[data-page=clusters]').click();await settle();assert.equal($('.cluster-card h3').textContent.includes('shared'),true);
  $('.cluster-card [data-paper="1"]').click();await settle();assert.equal($('#detail-notes').value,'Saved — збережено');
  $('#open-graph').click();await settle();
  assert.ok(requests.some(r=>r.url.startsWith('/api/graph?')&&new URL(r.url,'http://fixture.invalid').searchParams.get('seed_id')==='1'));
  const node=$('[data-node="2"]');
  node.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
  assert.equal($('#graph-selection h3').textContent,'Synthetic reference');assert.match($('#graph-selection').textContent,/openalex/);
  $('#graph-recenter').click();await settle();
  assert.equal(new URL(requests.filter(r=>r.url.startsWith('/api/graph?')).at(-1).url,'http://fixture.invalid').searchParams.get('seed_id'),'2');
  $('[data-node="1"]').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));
  $('#graph-open-paper').click();await settle();assert.equal($('#detail-notes').value,'Saved — збережено');
  assert.equal(w.document.documentElement.lang,locale);assert.equal($('.error'),null);
});
