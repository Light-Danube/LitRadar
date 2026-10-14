const {test}=require('node:test');
const assert=require('node:assert/strict');
const tools=require('../web/static/graph-tools.js');
const interactions=require('../web/static/graph-interactions.js');
const graph={seed_id:1,nodes:[{id:1,title:'Seed'},{id:2,title:'Reference'},{id:3,title:'Related'}],edges:[{source:'1',target:'2',type:'cites'},{source:'2',target:'3',type:'related'}]};
function separated(layout) {
  for(const [id,p] of layout.positions) {
    assert.ok(p.x>=20&&p.x<=layout.width-340&&p.y>=25&&p.y<=layout.height-25);
    for(const [other,q] of layout.positions)if(other!==id)
      assert.ok(Math.abs(p.x-q.x)>=tools.clearance.x||Math.abs(p.y-q.y)>=tools.clearance.y,`${id} overlaps ${other}`);
  }
}
test('saved overlapping positions settle deterministically without changing graph payload',()=>{
  const original=JSON.stringify(graph),custom={1:{x:400,y:200},2:{x:400,y:200},3:{x:400,y:200}};
  const layout=tools.layout(graph,custom);separated(layout);
  assert.deepEqual(layout,tools.layout({...graph,nodes:[...graph.nodes].reverse()},custom));
  assert.equal(JSON.stringify(graph),original);assert.deepEqual(custom[1],{x:400,y:200});
  assert.deepEqual(tools.layout(graph,Object.fromEntries(layout.positions)),layout);
});
test('bounded settling handles dense overlapping graphs and keeps a dragged node pinned',()=>{
  const dense={nodes:Array.from({length:80},(_,i)=>({id:i+1,title:'Wide label '+i})),edges:[],seed_id:1};
  const base=tools.layout(dense);
  for(const location of [{x:20,y:25},{x:base.width-340,y:base.height-25},{x:base.width/2,y:base.height/2}]) {
    const positions=new Map(dense.nodes.map(n=>[n.id,{...location}]));
    const settled=tools.settlePositions(positions,base.width,base.height,40);
    separated({...base,positions:settled});assert.deepEqual(settled.get(40),location);
    assert.deepEqual(settled,tools.settlePositions(positions,base.width,base.height,40));
  }
});
function fixture() {
  const makeElement=()=>({listeners:{},attrs:{},captures:new Set(),
    addEventListener(type,handler){this.listeners[type]=handler;},
    setAttribute(name,value){this.attrs[name]=String(value);},
    setPointerCapture(id){this.captures.add(id);},hasPointerCapture(id){return this.captures.has(id);},releasePointerCapture(id){this.captures.delete(id);}});
  const nodes=graph.nodes.map(n=>Object.assign(makeElement(),{dataset:{node:String(n.id)}}));
  for(const node of nodes)node.closest=()=>node;
  const lines=graph.edges.map(e=>Object.assign(makeElement(),{dataset:{source:e.source,target:e.target}}));
  const svg=Object.assign(makeElement(),{
    ownerDocument:{defaultView:{}},closest:()=>null,
    querySelectorAll(selector){return selector==='[data-node]'?nodes:lines;},
    getBoundingClientRect(){const base=tools.layout(graph);return {left:0,top:0,width:base.width,height:base.height};}
  });
  const saved=[];const controller=interactions.create(svg,graph,{save:positions=>saved.push(positions)});
  const event=(target,x,y,type='pointermove')=>({target,clientX:x,clientY:y,pointerId:1,button:0,type});
  return {nodes,lines,svg,saved,controller,event};
}
test('stationary node gesture captures the node, preserving native single-click selection',()=>{
  const {svg,nodes,controller,event,saved}=fixture(),before=controller.snapshot();
  svg.onpointerdown(event(nodes[0],40,45,'pointerdown'));
  assert.ok(nodes[0].hasPointerCapture(1));assert.ok(!svg.hasPointerCapture(1));
  svg.onpointerup(event(nodes[0],40,45,'pointerup'));
  assert.ok(!nodes[0].hasPointerCapture(1));assert.deepEqual(controller.snapshot(),before);assert.equal(saved.length,0);
  let suppressed=false;
  svg.listeners.click({stopImmediatePropagation(){suppressed=true;},preventDefault(){suppressed=true;}});
  assert.equal(suppressed,false);
});
test('dragging settles overlapping nodes, updates citation endpoints and saves only on completion',()=>{
  const {svg,nodes,lines,controller,event,saved}=fixture(),before=controller.snapshot();
  svg.onpointerdown(event(nodes[0],40,45,'pointerdown'));
  svg.onpointermove(event(nodes[0],380,45));
  assert.equal(saved.length,0);
  svg.onpointerup(event(nodes[0],380,45,'pointerup'));
  assert.equal(saved.length,1);assert.deepEqual(controller.snapshot()[1],before[2]);
  const base=tools.layout(graph);separated({...base,positions:new Map(Object.entries(controller.snapshot()).map(([id,p])=>[Number(id),p]))});
  assert.notEqual(controller.snapshot()[2].x,before[2].x);
  assert.ok(Number.isFinite(Number(lines[0].attrs.x1)));assert.notEqual(lines[0].attrs.x1,lines[0].attrs.x2);
  let suppressed=false;svg.listeners.click({stopImmediatePropagation(){suppressed=true;},preventDefault(){}});assert.ok(suppressed);
});
test('cancelled dragging restores position without saving; keyboard movement and reset remain available',()=>{
  const {svg,nodes,controller,event,saved}=fixture(),before=controller.snapshot();
  svg.onpointerdown(event(nodes[0],40,45,'pointerdown'));svg.onpointermove(event(nodes[0],140,145));
  svg.onpointercancel(event(nodes[0],140,145,'pointercancel'));
  assert.deepEqual(controller.snapshot(),before);assert.equal(saved.length,0);
  let prevented=false;nodes[0].listeners.keydown({shiftKey:true,key:'ArrowRight',preventDefault(){prevented=true;}});
  assert.ok(prevented);assert.equal(controller.snapshot()[1].x,before[1].x+20);assert.equal(saved.length,1);
  controller.resetLayout();assert.deepEqual(controller.snapshot(),before);assert.deepEqual(saved.at(-1),{});
});
