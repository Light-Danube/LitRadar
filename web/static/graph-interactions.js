(function(root) {
  'use strict';
  function zoomAt(view,base,factor,anchor={x:view.x+view.w/2,y:view.y+view.h/2}) {
    const w=Math.max(base.width/4,Math.min(base.width*2,view.w*factor)),h=w*base.height/base.width;
    return {x:anchor.x-(anchor.x-view.x)*w/view.w,y:anchor.y-(anchor.y-view.y)*h/view.h,w,h};
  }
  function create(svg,graph,{custom={},save=()=>{}}={}) {
    const base=root.GraphTools.layout(graph),initial=root.GraphTools.layout(graph,custom);
    let positions=new Map(initial.positions),view={x:0,y:0,w:base.width,h:base.height},drag=null,suppressClick=false;
    const nodes=new Map([...svg.querySelectorAll('[data-node]')].map(el=>[Number(el.dataset.node),el]));
    const point=event=>{
      const win=svg.ownerDocument.defaultView;
      if(svg.getScreenCTM && win.DOMPoint) return new win.DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());
      const rect=svg.getBoundingClientRect();
      return {x:view.x+(event.clientX-rect.left)*view.w/(rect.width||base.width),y:view.y+(event.clientY-rect.top)*view.h/(rect.height||base.height)};
    };
    const update=()=>svg.setAttribute('viewBox',`${view.x} ${view.y} ${view.w} ${view.h}`);
    function move(id,x,y) {
      const p={x:Math.max(20,Math.min(base.width-340,x)),y:Math.max(25,Math.min(base.height-25,y))};
      positions.set(id,p);
      const original=initial.positions.get(id);
      nodes.get(id).setAttribute('transform',`translate(${p.x-original.x} ${p.y-original.y})`);
      svg.querySelectorAll('line[data-source]').forEach(line=>{
        const a=positions.get(Number(line.dataset.source)),b=positions.get(Number(line.dataset.target));
        if(!a||!b)return;
        const length=Math.hypot(b.x-a.x,b.y-a.y),ux=length?(b.x-a.x)/length:1,uy=length?(b.y-a.y)/length:0;
        for(const [key,value] of Object.entries({x1:a.x+ux*14,y1:a.y+uy*14,x2:b.x-ux*17,y2:b.y-uy*17}))line.setAttribute(key,value);
      });
    }
    function settle(pinned) {
      const next=root.GraphTools.settlePositions(positions,base.width,base.height,pinned);
      for(const [id,p] of next)move(id,p.x,p.y);
    }
    const snapshot=()=>Object.fromEntries(positions);
    const persist=()=>save(snapshot());
    function zoom(factor,anchor){view=zoomAt(view,base,factor,anchor);update();}
    svg.addEventListener('wheel',event=>{
      if(!event.deltaY)return;
      event.preventDefault();
      if(drag)return;
      const delta=event.deltaY*(event.deltaMode===1?16:event.deltaMode===2?base.height:1);
      zoom(Math.exp(Math.max(-300,Math.min(300,delta))*.0015),point(event));
    },{passive:false});
    svg.onpointerdown=event=>{
      if(event.button!==0)return;
      const node=event.target.closest('[data-node]'),p=point(event),id=node?Number(node.dataset.node):null;
      // Capture on the original node, so a stationary gesture produces a native
      // node click. Capturing on the SVG retargets that click to the background.
      const capture=node||svg;
      drag={viewOrigin:{...view},capture,pointer:event.pointerId,id,start:p,last:p,moved:false,client:{x:event.clientX,y:event.clientY},origin:id===null?null:{...positions.get(id)}};
      capture.setPointerCapture?.(event.pointerId);
    };
    svg.onpointermove=event=>{
      if(!drag||drag.pointer!==event.pointerId)return;
      if(Math.hypot(event.clientX-drag.client.x,event.clientY-drag.client.y)<4&&!drag.moved)return;
      drag.moved=true;const p=point(event);
      if(drag.id!==null)move(drag.id,drag.origin.x+p.x-drag.start.x,drag.origin.y+p.y-drag.start.y);
      else {view.x+=drag.last.x-p.x;view.y+=drag.last.y-p.y;update();}
    };
    function finish(event){
      if(!drag||event.pointerId!==drag.pointer)return;
      const old=drag;drag=null;
      if(event.type==='pointercancel') {
        if(old.id!==null)move(old.id,old.origin.x,old.origin.y);else {view={...old.viewOrigin};update();}
      } else if(old.moved) {
        suppressClick=true;setTimeout(()=>{suppressClick=false;},0);
        if(old.id!==null){settle(old.id);persist();}
      }
      if(old.capture.hasPointerCapture?.(event.pointerId))old.capture.releasePointerCapture(event.pointerId);
    }
    svg.onpointerup=svg.onpointercancel=svg.onlostpointercapture=finish;
    svg.addEventListener('click',event=>{if(suppressClick){event.stopImmediatePropagation();event.preventDefault();}},{capture:true});
    for(const [id,node] of nodes)node.addEventListener('keydown',event=>{
      const directions={ArrowLeft:[-20,0],ArrowRight:[20,0],ArrowUp:[0,-20],ArrowDown:[0,20]};
      if(event.shiftKey&&directions[event.key]) {
        event.preventDefault();const p=positions.get(id),[dx,dy]=directions[event.key];move(id,p.x+dx,p.y+dy);settle(id);persist();
      }
    });
    return {zoom,snapshot,resetView(){view={x:0,y:0,w:base.width,h:base.height};update();},
      resetLayout(){for(const [id,p] of base.positions)move(id,p.x,p.y);save({});this.resetView();}};
  }
  const api={zoomAt,create};root.GraphInteractions=api;
  if(typeof module!=='undefined')module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
