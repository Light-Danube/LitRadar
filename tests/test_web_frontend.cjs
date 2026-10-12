const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const graphTools=require('../web/static/graph-tools.js');
const i18n=require('../web/static/locales.js');
const sample={seed_id:1,nodes:[{id:1,title:'Українська <script>& "title"',source:'fixture',status:'new'},
  {id:2,title:'Reference',source:'openalex',published_at:'2022-01-01',status:'read'},
  {id:3,title:'Related',source:'fixture',status:'new'}],edges:[
    {source:'1',target:'2',type:'cites',provenance:[{provider:'openalex',observed_at:'2026'}]},
    {source:'1',target:'3',type:'related',provenance:[]}],year_from:2020};
test('layered layout is deterministic, bounded and separates dense node labels',()=>{
  const graph={nodes:Array.from({length:80},(_,i)=>({id:i+1,title:'Node '+i})),edges:sample.edges,seed_id:1};
  const layout=graphTools.layout(graph),again=graphTools.layout({...graph,nodes:[...graph.nodes].reverse()});
  assert.deepEqual(layout,again);assert.equal(layout.positions.size,80);
  for(const [id,p] of layout.positions){assert.ok(p.x>=10&&p.x+210<layout.width);assert.ok(p.y>=10&&p.y+15<layout.height);
    for(const [other,q] of layout.positions)if(id!==other)assert.ok(Math.abs(p.x-q.x)>=250||Math.abs(p.y-q.y)>=60);}
});
test('SVG export escapes titles, includes arrow direction and undirected dashes',()=>{
  const svg=graphTools.svg(sample,'Граф');assert.ok(svg.includes('xmlns="http://www.w3.org/2000/svg"'));
  assert.ok(svg.includes('marker-end="url(#citation-arrow)"'));assert.ok(svg.includes('stroke-dasharray="5 5"'));
  assert.ok(svg.includes('&lt;script&gt;'));assert.ok(!svg.includes('<script>'));assert.ok(svg.includes('Українська'));
});
test('GraphML export preserves node identities, types and provenance',()=>{
  const xml=graphTools.graphml(sample);assert.ok(xml.includes('source="n1" target="n2" directed="true"'));
  assert.ok(xml.includes('source="n1" target="n3" directed="false"'));assert.ok(xml.includes('openalex'));
  assert.ok(xml.includes('&lt;script&gt;'));assert.ok(xml.includes('attr.name="provenance"'));
});
test('both locales cover every static interface key and preserve interpolation',()=>{
  const app=fs.readFileSync(require.resolve('../web/static/app.js'),'utf8');
  for(const match of app.matchAll(/\bt\('([^']+)'(?:\)|,)/g))assert.ok(i18n.dictionaries.en[match[1]],match[1]);
  for(const match of app.matchAll(/\b(?:button|field)\('[^']+','([^']+)'/g))assert.ok(i18n.dictionaries.en[match[1]],match[1]);
  for(const key of Object.keys(i18n.dictionaries.en)){assert.ok(i18n.dictionaries.uk[key]);
    assert.deepEqual(i18n.dictionaries.en[key].match(/\{\{\w+\}\}/g),i18n.dictionaries.uk[key].match(/\{\{\w+\}\}/g),key);}
  assert.equal(i18n.translate('uk','count',{count:12}),'Публікацій: 12');
});
