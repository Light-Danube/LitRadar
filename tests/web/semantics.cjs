const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.resolve(__dirname,'../..');
const settle=async()=>{for(let i=0;i<15;i++)await new Promise(resolve=>setImmediate(resolve));};
for(const locale of ['en','uk'])test(`semantic graph/clusters require explicit selection and label computed results (${locale})`,async t=>{
  const dom=new JSDOM(fs.readFileSync(path.join(root,'web/index.html'),'utf8'),{url:'http://fixture.invalid',runScripts:'outside-only'});
  t.after(()=>dom.window.close());const w=dom.window,$=selector=>w.document.querySelector(selector),requests=[];let failSemantic=false;
  w.localStorage.setItem('litbeacon-language',locale);w.matchMedia=()=>({matches:false,addEventListener(){}});
  const papers=[1,2].map(id=>({id,title:'Synthetic related '+id,abstract:'Synthetic',status:'new',tags:[],notes:'',authors:[],relevance_score:.5}));
  w.fetch=async url=>{
    requests.push(url);const parsed=new URL(url,'http://fixture.invalid');let data;
    if(failSemantic&&parsed.searchParams.get('mode')==='semantic')return {ok:false,status:503,json:async()=>({detail:'Synthetic unavailable model'})};
    const metadata={method:'embedding',model:'synthetic-local',threshold:.72,evaluated_nodes:2};
    if(parsed.pathname==='/api/health')data={database:'synthetic',semantic_workspace:{enabled:true,configured:true}};
    else if(parsed.pathname==='/api/summary')data={stats:{all:2},recent:papers,reading_queue:[]};
    else if(parsed.pathname==='/api/graph') {
      const active=parsed.searchParams.get('include_semantic')==='true';
      data={nodes:papers,edges:active?[{source:'1',target:'2',type:'related',provider:'embedding:synthetic-local',provenance:[{provider:'embedding:synthetic-local',model:'synthetic-local',similarity:1,ephemeral:true,observed_at:null}]}]:[],providers:[],semantic:active?metadata:null};
    } else if(parsed.pathname==='/api/clusters')data={...metadata,method:parsed.searchParams.get('mode')==='semantic'?'embedding':'heuristic',clusters:[{label:'Synthetic computed group',size:2,papers}]};
    else throw new Error('Unexpected synthetic request '+url);
    return {ok:true,json:async()=>data};
  };
  for(const name of ['theme','locales','graph-tools','graph-interactions','annotation-workflows','app'])w.eval(fs.readFileSync(path.join(root,`web/static/${name}.js`),'utf8'));
  await settle();$('[data-page=graph]').click();await settle();
  const checkbox=$('#graph-semantic');assert.equal(checkbox.disabled,false);assert.equal(checkbox.checked,false);
  assert.ok(!requests.some(url=>url.includes('include_semantic=true')));
  checkbox.checked=true;$('#graph-filters').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await settle();
  assert.ok(requests.some(url=>url.includes('include_semantic=true')));assert.ok($('#page-content').textContent.includes('synthetic-local'));
  $('[data-node]').dispatchEvent(new w.MouseEvent('click',{bubbles:true}));assert.ok($('#graph-selection').textContent.includes('1.000'));assert.ok(!$('#graph-selection').textContent.includes('null'));
  $('[data-page=clusters]').click();await settle();const select=$('#cluster-mode');assert.equal(select.value,'heuristic');
  select.value='semantic';select.dispatchEvent(new w.Event('change'));await settle();
  assert.ok(requests.some(url=>url.includes('mode=semantic')));assert.ok($('#page-content').textContent.includes('Synthetic computed group'));
  failSemantic=true;$('#cluster-mode').dispatchEvent(new w.Event('change'));await settle();
  assert.ok($('#disable-semantic'));$('#disable-semantic').click();await settle();assert.equal($('#cluster-mode').value,'heuristic');
});
