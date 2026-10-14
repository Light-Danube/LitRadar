(function (root) {
  'use strict';
  const xml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
  // Text is capped at 28 characters; reserve its entire label and circle footprint.
  // This is a bounded settling pass, not a continuously running force simulation.
  const clearance={x:330,y:52};
  function settlePositions(positions,width,height,pinned=null) {
    const bounds=p=>({x:Math.max(20,Math.min(width-340,p.x)),y:Math.max(25,Math.min(height-25,p.y))});
    const overlaps=(p,q)=>Math.abs(p.x-q.x)<clearance.x && Math.abs(p.y-q.y)<clearance.y;
    const ids=[...positions.keys()].sort((a,b)=>a-b);
    if(positions.has(pinned))ids.splice(0,0,...ids.splice(ids.indexOf(pinned),1));
    const grid=[];
    for(let y=25;y<=height-25;y+=clearance.y)for(let x=20;x<=width-340;x+=clearance.x)grid.push({x,y});
    function place(useOriginal) {
      const result=new Map();
      for(const id of ids) {
        const original=bounds(positions.get(id));
        const candidates=(useOriginal||id===pinned?[original]:[]).concat(grid).sort((a,b)=>
          Math.hypot(a.x-original.x,a.y-original.y)-Math.hypot(b.x-original.x,b.y-original.y)||a.y-b.y||a.x-b.x);
        const free=candidates.find(p=>![...result.values()].some(q=>overlaps(p,q)));
        if(!free)return null;
        result.set(id,{...free});
      }
      return result;
    }
    // If arbitrary saved positions fragmented the free space, repack on the grid.
    return place(true)||place(false)||new Map([...positions].map(([id,p])=>[id,bounds(p)]));
  }
  function layout(graph, custom={}) {
    const nodes = [...graph.nodes].sort((a,b)=>a.id-b.id), ids=new Set(nodes.map(n=>n.id));
    const seed=ids.has(graph.seed_id)?graph.seed_id:nodes[0]?.id;
    const neighbors=new Map(nodes.map(n=>[n.id,new Set()]));
    for(const e of graph.edges) {
      const a=Number(e.source),b=Number(e.target);
      if(ids.has(a)&&ids.has(b)){neighbors.get(a).add(b);neighbors.get(b).add(a);}
    }
    const distance=new Map(seed===undefined?[]:[[seed,0]]),queue=seed===undefined?[]:[seed];
    for(let i=0;i<queue.length;i++)for(const id of [...neighbors.get(queue[i])].sort((a,b)=>a-b)) {
      if(!distance.has(id)){distance.set(id,distance.get(queue[i])+1);queue.push(id);}
    }
    const groups=new Map();
    for(const n of nodes){const level=distance.get(n.id)??Math.max(1,...distance.values())+1;if(!groups.has(level))groups.set(level,[]);groups.get(level).push(n);}
    const positions=new Map();let column=0,maxRows=1;
    for(const [,group] of [...groups].sort((a,b)=>a[0]-b[0])) {
      group.forEach((n,i)=>{positions.set(n.id,{x:40+(column+Math.floor(i/8))*340,y:45+(i%8)*65});});
      column+=Math.ceil(group.length/8);maxRows=Math.max(maxRows,Math.min(8,group.length));
    }
    const width=Math.max(900,column*340+40),height=Math.max(510,maxRows*65+30);
    for(const [id,p] of positions) {
      const saved=custom[id];
      if(saved && Number.isFinite(saved.x) && Number.isFinite(saved.y))
        positions.set(id,{x:Math.max(20,Math.min(width-340,saved.x)),y:Math.max(25,Math.min(height-25,saved.y))});
    }
    return {positions:settlePositions(positions,width,height),width,height};
  }
  function svg(graph, title='Citation map', empty='No stored relationships', custom={}) {
    const {positions,width,height}=layout(graph,custom);
    const lines=graph.edges.map(e=>{
      const a=positions.get(Number(e.source)),b=positions.get(Number(e.target));if(!a||!b)return '';
      const length=Math.hypot(b.x-a.x,b.y-a.y);
      const ux=length?(b.x-a.x)/length:1,uy=length?(b.y-a.y)/length:0;
      return `<line data-source="${xml(e.source)}" data-target="${xml(e.target)}" x1="${a.x+ux*14}" y1="${a.y+uy*14}" x2="${b.x-ux*17}" y2="${b.y-uy*17}" stroke="${e.type==='related'?'#e2bd7c':'#8cc8f2'}" stroke-width="1.6" ${e.type==='related'?'stroke-dasharray="5 5"':'marker-end="url(#citation-arrow)"'}><title>${xml((e.provenance||[]).map(p=>p.ephemeral?`Computed similarity: ${p.model||p.provider}; cosine ${p.similarity}`:`${p.provider} (${p.observed_at})`).join('; '))}</title></line>`;
    }).join('');
    const circles=graph.nodes.map(n=>{
      const p=positions.get(n.id),fill=n.id===graph.seed_id?'#42cfb1':n.status==='to-read'?'#e2bd7c':'#63b3ff';
      const short=n.title.length>28?n.title.slice(0,26)+'…':n.title;
      return `<g data-node="${n.id}" tabindex="0" role="button" aria-label="${xml(n.title)}"><title>${xml(n.title)}</title><circle class="node${n.id===graph.seed_id?' seed':n.status==='to-read'?' todo':''}" cx="${p.x}" cy="${p.y}" r="11" fill="${fill}" stroke="#eaf2ff" stroke-width="2"/><text x="${p.x+18}" y="${p.y-17}" fill="#eaf2ff" font-family="sans-serif" font-size="11">${xml(short)}</text></g>`;
    }).join('');
    return `<svg xmlns="http://www.w3.org/2000/svg" id="graph-svg" class="graph-svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="group" aria-label="${xml(title)}"><title>${xml(title)}</title><rect width="100%" height="100%" fill="#091726"/><defs><marker id="citation-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0 L10 5 L0 10z" fill="#8cc8f2"/></marker></defs>${lines}${circles}${graph.nodes.length?'':`<text x="40" y="80" fill="#eaf2ff" font-family="sans-serif">${xml(empty)}</text>`}</svg>`;
  }
  function graphml(graph) {
    const keys=[['title','node'],['year','node'],['source','node'],['type','edge'],['provenance','edge']];
    return `<?xml version="1.0" encoding="UTF-8"?><graphml xmlns="http://graphml.graphdrawing.org/xmlns">${keys.map(([key,scope])=>`<key id="${key}" for="${scope}" attr.name="${key}" attr.type="string"/>`).join('')}<graph id="LitBeacon" edgedefault="directed">${graph.nodes.map(n=>`<node id="n${n.id}"><data key="title">${xml(n.title)}</data><data key="year">${xml(n.published_at)}</data><data key="source">${xml(n.source)}</data></node>`).join('')}${graph.edges.map((e,i)=>`<edge id="e${i}" source="n${xml(e.source)}" target="n${xml(e.target)}" directed="${e.type==='cites'}"><data key="type">${xml(e.type)}</data><data key="provenance">${xml(JSON.stringify(e.provenance||[]))}</data></edge>`).join('')}</graph></graphml>`;
  }
  const api={layout,settlePositions,clearance,svg,graphml};root.GraphTools=api;
  if(typeof module!=='undefined')module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
