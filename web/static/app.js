const state = { page: 'overview', papers: [], selected: null, query: '', status: 'all', sort: 'relevance_score', graphSeed: null, clusterData: null };
state.graphFilters = { relation: 'all', provider: '', depth: '1' };
state.graphRequest = 0;
const $ = (selector, root = document) => root.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const titleOf = (paper) => paper?.title || `Paper #${paper?.id ?? '?'}`;
const yearOf = (paper) => (paper?.published_at || '').slice(0, 4) || 'Year n/a';
const scoreOf = (paper) => Number(paper?.relevance_score ?? 0);
async function api(url, options = {}) {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `${response.status} ${response.statusText}`);
  return payload;
}
function toast(message, isError = false) { const el = $('#toast'); el.textContent = message; el.style.background = isError ? '#4b2432' : '#163c3d'; el.classList.add('show'); clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove('show'), 3100); }
function switchPage(page) { state.page = page; document.querySelectorAll('.nav-item').forEach(btn => btn.classList.toggle('active', btn.dataset.page === page)); renderPage(); }
document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => switchPage(btn.dataset.page)));
$('#refresh').addEventListener('click', () => renderPage());
function paperRow(paper) { const score = scoreOf(paper); return `<article class="paper-row"><div><div class="paper-title" data-paper="${paper.id}">${esc(titleOf(paper))}</div><div class="paper-meta"><span>${esc(yearOf(paper))}</span><span>${esc(paper.source || 'unknown source')}</span><span>${Number(paper.citation_count || 0)} citations</span><span class="status">${esc(paper.status)}</span></div></div><span class="score ${score < .45 ? 'low' : ''}">${Math.round(score*100)}%</span></article>`; }
function bindPaperClicks(root = document) { root.querySelectorAll('[data-paper]').forEach(el => el.addEventListener('click', async () => { const id = Number(el.dataset.paper); await loadDetail(id); switchPage('inbox'); })); }
async function renderPage() {
  const container = $('#page-content');
  const titles = { overview:'Overview', inbox:'Literature inbox', graph:'Citation map', clusters:'Literature clusters', jobs:'Scheduled jobs' };
  $('#page-title').textContent = titles[state.page] || 'Workspace';
  container.innerHTML = '<div class="loading">Loading workspace…</div>';
  try {
    if (state.page === 'overview') await renderOverview(container);
    if (state.page === 'inbox') await renderInbox(container);
    if (state.page === 'graph') await renderGraph(container);
    if (state.page === 'clusters') await renderClusters(container);
    if (state.page === 'jobs') await renderJobs(container);
  } catch (error) { container.innerHTML = `<div class="error">${esc(error.message)}<br><br>Check that the LitBeacon web server is running and that the local SQLite library is readable.</div>`; }
}
async function renderOverview(container) {
  const data = await api('/api/summary');
  const stats = data.stats || {};
  container.innerHTML = `<div class="cards">
    <div class="metric"><span class="label">Library papers</span><strong>${stats.all || 0}</strong><small>All stored records</small></div>
    <div class="metric"><span class="label">New to review</span><strong>${stats.new || 0}</strong><small>Untriaged discoveries</small></div>
    <div class="metric"><span class="label">Reading queue</span><strong>${stats['to-read'] || 0}</strong><small>Marked to read</small></div>
    <div class="metric"><span class="label">Read</span><strong>${stats.read || 0}</strong><small>Marked as read</small></div>
  </div><div class="split"><section class="panel"><div class="panel-head"><h2>Recently added</h2><button class="link-button" data-goto="inbox">Open inbox →</button></div><div class="paper-list">${data.recent.length ? data.recent.map(paperRow).join('') : '<div class="empty">No papers yet. Use the CLI/TUI to search and ingest the first papers.</div>'}</div></section><section class="panel"><div class="panel-head"><h2>Reading queue</h2><button class="link-button" data-goto="inbox">Review →</button></div><div class="paper-list">${data.reading_queue.length ? data.reading_queue.map(paperRow).join('') : '<div class="empty">The queue is empty. Mark a paper as “to-read” from the inbox.</div>'}</div><div class="notice">Scores help prioritize exploration; they do not establish novelty or research quality by themselves.</div></section></div>`;
  bindPaperClicks(container); container.querySelectorAll('[data-goto]').forEach(el=>el.addEventListener('click',()=>switchPage(el.dataset.goto)));
}
async function loadPapers() { const params = new URLSearchParams({ q:state.query, status:state.status, sort:state.sort, limit:'200' }); const data = await api(`/api/papers?${params}`); state.papers=data.items; return data; }
async function renderInbox(container) {
  const data = await loadPapers();
  const statuses = ['all','new','to-read','read','archived','dismissed'];
  container.innerHTML = `<div class="toolbar"><input class="field search" id="paper-search" placeholder="Search title, abstract, venue or notes…" value="${esc(state.query)}"><select class="field" id="status-filter">${statuses.map(status=>`<option value="${status}" ${state.status===status?'selected':''}>${status==='all'?'All statuses':status}</option>`).join('')}</select><select class="field" id="sort-filter">${[['relevance_score','Relevance'],['recent','Newest publication'],['newest_added','Recently added'],['citations','Most cited'],['title','Title A–Z']].map(([v,l])=>`<option value="${v}" ${state.sort===v?'selected':''}>${l}</option>`).join('')}</select><span class="badge">${data.count} papers</span></div><div class="inbox-layout"><section class="panel table-list"><div class="panel-head"><h2>Library</h2><span class="muted">Select a paper for details</span></div><div class="paper-list">${data.items.length ? data.items.map(paperRow).join('') : '<div class="empty">No matching papers.</div>'}</div></section><section class="panel" id="detail-panel"><div class="empty">Select a paper from the list to edit notes, tags and status.</div></section></div>`;
  $('#paper-search',container).addEventListener('input', event => { clearTimeout(renderInbox.timer); renderInbox.timer=setTimeout(()=>{state.query=event.target.value;renderInbox($('#page-content'));},180); });
  $('#status-filter',container).addEventListener('change',event=>{state.status=event.target.value;renderInbox($('#page-content'));}); $('#sort-filter',container).addEventListener('change',event=>{state.sort=event.target.value;renderInbox($('#page-content'));});
  bindPaperClicks(container);
  if (state.selected) renderDetail(state.selected, $('#detail-panel',container));
}
async function loadDetail(id) { state.selected=await api(`/api/papers/${id}`); const panel=$('#detail-panel'); if(state.page==='inbox'&&panel) renderDetail(state.selected,panel); }
function renderDetail(paper, panel) {
  if(!panel) return;
  const authors = Array.isArray(paper.authors) ? paper.authors.map(a=>typeof a==='string'?a:(a.name||'')).filter(Boolean).slice(0,6).join(', ') : '';
  const url = paper.doi ? `https://doi.org/${paper.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//i,'')}` : paper.url;
  panel.innerHTML = `<div class="panel-head"><h2>Paper detail</h2><span class="badge">#${paper.id}</span></div><h2 class="detail-title">${esc(titleOf(paper))}</h2><div class="paper-meta"><span>${esc(authors || 'Authors not indexed')}</span><span>${esc(yearOf(paper))}</span><span>${esc(paper.venue || paper.source)}</span></div><div class="paper-meta" style="margin:12px 0"><span class="score">Score ${Math.round(scoreOf(paper)*100)}%</span><span>${Number(paper.citation_count||0)} citations</span>${paper.reference_count!=null?`<span>${paper.reference_count} references</span>`:''}</div><p class="abstract">${esc(paper.abstract || 'No abstract available.')}</p>${url?`<p><a class="link-button" href="${esc(url)}" target="_blank" rel="noreferrer">Open paper ↗</a></p>`:''}<div class="detail-fields"><label>Status<select id="detail-status" class="field">${['new','to-read','read','archived','dismissed'].map(v=>`<option value="${v}" ${v===paper.status?'selected':''}>${v}</option>`).join('')}</select></label><label>Tags <small class="muted">comma-separated</small><input class="field tags-input" id="detail-tags" value="${esc((paper.tags||[]).join(', '))}" placeholder="context, sarcasm, method"></label><label>Research notes<textarea class="field" id="detail-notes" placeholder="What matters for your dissertation? Key method, limitation, open question…">${esc(paper.notes||'')}</textarea></label></div><div class="detail-actions"><button id="save-annotation" class="btn primary">Save annotations</button><button id="open-graph" class="btn">Explore links</button></div>`;
  $('#save-annotation',panel).addEventListener('click', async ()=>{try{const saved=await api(`/api/papers/${paper.id}`,{method:'PATCH',body:JSON.stringify({status:$('#detail-status',panel).value,tags:$('#detail-tags',panel).value.split(',').map(t=>t.trim()).filter(Boolean),notes:$('#detail-notes',panel).value})});state.selected=saved;toast('Annotations saved to local SQLite.');}catch(e){toast(e.message,true);}});
  $('#detail-status',panel).addEventListener('change',()=>$('#save-annotation',panel).classList.add('primary'));
  $('#open-graph',panel).addEventListener('click',()=>{state.graphSeed=paper.id;switchPage('graph');});
}
async function renderGraph(container) {
  const request=++state.graphRequest;
  const seed=state.graphSeed || state.selected?.id || null;
  const params=new URLSearchParams({depth:state.graphFilters.depth,max_nodes:'80',relation:state.graphFilters.relation}); if(seed)params.set('seed_id',seed);
  if(state.graphFilters.provider)params.set('provider',state.graphFilters.provider);
  const graph=await api(`/api/graph?${params}`);
  if(request!==state.graphRequest||state.page!=='graph')return;
  container.innerHTML=`<section class="panel"><div class="panel-head"><div><h2>Citation & related-work map</h2><p class="muted">Stored local relationships only · select a node to inspect its links</p></div><button class="btn" id="refresh-graph">↻ Refresh map</button></div>
  <div class="toolbar"><label>Relation <select class="field" id="graph-relation">${[['all','All relations'],['cites','Citations'],['related','Related work']].map(([v,l])=>`<option value="${v}" ${state.graphFilters.relation===v?'selected':''}>${l}</option>`).join('')}</select></label><label>Edge provider <select class="field" id="graph-provider"><option value="">All providers</option>${graph.providers.map(v=>`<option value="${esc(v)}" ${state.graphFilters.provider===v?'selected':''}>${esc(v)}</option>`).join('')}</select></label><label>Depth <select class="field" id="graph-depth">${['1','2'].map(v=>`<option ${state.graphFilters.depth===v?'selected':''}>${v}</option>`).join('')}</select></label><button class="btn" id="reset-graph-filters">Reset filters</button></div>
  <div class="legend"><span><i class="dot seed"></i>Neighborhood seed</span><span><i class="dot"></i>New / untriaged</span><span>→ citing paper to cited paper (reference)</span><span>← incoming citation (cited by)</span><span>Dashed — related work (undirected)</span></div><div class="toolbar"><button class="btn" id="graph-zoom-in" aria-label="Zoom in">+</button><button class="btn" id="graph-zoom-out" aria-label="Zoom out">−</button><button class="btn" id="graph-reset-view">Reset view</button><span class="muted">Drag background to pan</span></div><div class="svg-wrap"><svg id="graph-svg" class="graph-svg" viewBox="0 0 900 510" role="group" aria-label="Citation relationship graph"></svg></div><p class="muted">${graph.nodes.length} nodes · ${graph.edges.length} unique relationships${graph.truncated?' · node limit reached':''}. Only matching edges are traversed. Missing links may not have been fetched; use Citation Discovery in CLI/TUI.</p><div id="graph-selection" aria-live="polite"><p class="muted">Select a node with click, Enter or Space.</p></div><div id="graph-paper-list" class="paper-list">${graph.nodes.slice(0,8).map(paperRow).join('')}</div></section>`;
  for(const key of ['relation','provider','depth']) $(`#graph-${key}`,container).addEventListener('change',event=>{state.graphFilters[key]=event.target.value;renderGraph(container).catch(e=>toast(e.message,true));});
  $('#reset-graph-filters',container).addEventListener('click',()=>{state.graphFilters={relation:'all',provider:'',depth:'1'};renderGraph(container).catch(e=>toast(e.message,true));});
  $('#refresh-graph',container).addEventListener('click',()=>renderGraph(container).catch(e=>toast(e.message,true))); bindPaperClicks(container); drawGraph(graph, $('#graph-svg',container));
  const svg=$('#graph-svg',container), view={x:0,y:0,w:900,h:510};
  const update=()=>svg.setAttribute('viewBox',`${view.x} ${view.y} ${view.w} ${view.h}`);
  const zoom=factor=>{const w=Math.max(225,Math.min(1800,view.w*factor)),h=w*510/900;view.x+=(view.w-w)/2;view.y+=(view.h-h)/2;view.w=w;view.h=h;update();};
  $('#graph-zoom-in',container).addEventListener('click',()=>zoom(.8));
  $('#graph-zoom-out',container).addEventListener('click',()=>zoom(1.25));
  $('#graph-reset-view',container).addEventListener('click',()=>{Object.assign(view,{x:0,y:0,w:900,h:510});update();});
  let drag=null;
  svg.addEventListener('pointerdown',event=>{if(event.button!==0||event.target.closest('[data-node]'))return;const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());drag={point,id:event.pointerId};svg.setPointerCapture(event.pointerId);});
  svg.addEventListener('pointermove',event=>{if(!drag||event.pointerId!==drag.id)return;const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());view.x+=drag.point.x-point.x;view.y+=drag.point.y-point.y;update();});
  svg.addEventListener('pointerup',()=>{drag=null;});svg.addEventListener('pointercancel',()=>{drag=null;});svg.addEventListener('lostpointercapture',()=>{drag=null;});
}
function selectGraphNode(paper, graph, svg) {
  svg.querySelectorAll('[data-node]').forEach(el=>el.classList.toggle('selected',Number(el.dataset.node)===paper.id));
  const nodes=new Map(graph.nodes.map(p=>[String(p.id),p]));
  const links=graph.edges.filter(e=>Number(e.source)===paper.id||Number(e.target)===paper.id);
  const panel=$('#graph-selection');
  panel.innerHTML=`<h3>${esc(titleOf(paper))}</h3><div class="detail-actions"><button class="btn" id="graph-open-paper">Open paper</button><button class="btn" id="graph-recenter">Explore this neighborhood</button></div><ul class="graph-links">${links.map(e=>{const outgoing=Number(e.source)===paper.id;const other=nodes.get(outgoing?e.target:e.source);return `<li>${e.type==='related'?'Related work':outgoing?'References':'Cited by'}: ${esc(titleOf(other))}<br><small class="muted">${e.provenance.map(p=>`${esc(p.provider)} · observed ${esc(p.observed_at)}`).join('; ')}</small></li>`;}).join('')||'<li>No matching stored links for this paper.</li>'}</ul>`;
  $('#graph-open-paper',panel).addEventListener('click',async()=>{try{await loadDetail(paper.id);switchPage('inbox');}catch(e){toast(e.message,true);}});
  $('#graph-recenter',panel).addEventListener('click',()=>{state.graphSeed=paper.id;renderGraph($('#page-content')).catch(e=>toast(e.message,true));});
}
function drawGraph(graph, svg) {
  const ns='http://www.w3.org/2000/svg', width=900, height=510; svg.innerHTML='';
  const make=(tag,attrs={})=>{const el=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,String(v)));return el;};
  if(!graph.nodes.length){const text=make('text',{x:450,y:245,'text-anchor':'middle',class:'node-label'});text.textContent='No papers in this graph yet';svg.append(text);return;}
  const centerIndex=graph.nodes.findIndex(p=>p.id===graph.seed_id); const center=Math.max(0,centerIndex); const positions=new Map(); positions.set(graph.nodes[center].id,{x:450,y:255});
  const others=graph.nodes.filter((_,i)=>i!==center); others.forEach((paper,i)=>{const angle=2*Math.PI*i/Math.max(others.length,1)-Math.PI/2;const radius=others.length<8?115:Math.min(210,100+others.length*3);positions.set(paper.id,{x:450+Math.cos(angle)*radius,y:255+Math.sin(angle)*radius*.78});});
  const defs=make('defs'),marker=make('marker',{id:'citation-arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:8,markerHeight:8,orient:'auto',markerUnits:'userSpaceOnUse'});
  marker.append(make('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:'#8cc8f2'}));defs.append(marker);svg.append(defs);
  const radius=paper=>paper.id===graph.seed_id?16:scoreOf(paper)>.75?11:8;
  const papers=new Map(graph.nodes.map(p=>[p.id,p]));
  for(const edge of graph.edges){const source=Number(edge.source),target=Number(edge.target),a=positions.get(source),b=positions.get(target);if(!a||!b||source===target)continue;const distance=Math.hypot(b.x-a.x,b.y-a.y),ux=(b.x-a.x)/distance,uy=(b.y-a.y)/distance;
    const line=make('line',{x1:a.x+ux*(radius(papers.get(source))+3),y1:a.y+uy*(radius(papers.get(source))+3),x2:b.x-ux*(radius(papers.get(target))+4),y2:b.y-uy*(radius(papers.get(target))+4),class:`edge ${edge.type==='related'?'related':''}`});
    if(edge.type==='cites')line.setAttribute('marker-end','url(#citation-arrow)');
    const title=make('title');title.textContent=`${titleOf(papers.get(source))} ${edge.type==='cites'?'cites':'is related to'} ${titleOf(papers.get(target))} · ${edge.provenance.map(p=>`${p.provider} (${p.observed_at})`).join('; ')}`;line.append(title);svg.append(line);
  }
  for(const paper of graph.nodes){const pos=positions.get(paper.id);const group=make('g',{'data-node':paper.id,tabindex:0,role:'button','aria-label':titleOf(paper)});const classes=['node',paper.id===graph.seed_id?'seed':paper.status==='to-read'?'todo':paper.status==='read'?'read':'new'].join(' ');const circle=make('circle',{cx:pos.x,cy:pos.y,r:radius(paper),class:classes});group.append(circle);const label=make('text',{x:pos.x+14,y:pos.y+3,class:'node-label'});label.textContent=titleOf(paper).length>33?titleOf(paper).slice(0,31)+'…':titleOf(paper);group.append(label);group.addEventListener('click',()=>selectGraphNode(paper,graph,svg));group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selectGraphNode(paper,graph,svg);}});svg.append(group);}
}
async function renderClusters(container) {
  const data=await api('/api/clusters?limit=400'); state.clusterData=data;
  container.innerHTML=`<section class="panel"><div class="panel-head"><div><h2>Literature clusters</h2><p class="muted">Exploratory groupings from the current local corpus</p></div><span class="badge">${data.clusters.length} groups</span></div><div class="notice">${esc(data.description)} These are heuristic clusters, not embedding-based semantic groupings and not proof of a research gap.</div><div class="cluster-grid">${data.clusters.map((cluster,index)=>`<article class="cluster-card"><h3>${esc(cluster.label)}</h3><div class="count">${cluster.size}</div><p>${esc(cluster.method)} · papers</p><div class="cluster-papers">${cluster.papers.slice(0,6).map(p=>`<div class="cluster-paper" data-paper="${p.id}">${esc(titleOf(p))}</div>`).join('')||'<span class="muted">No sample papers</span>'}</div></article>`).join('')||'<div class="empty">Add more papers to build local clusters.</div>'}</div></section>`;
  bindPaperClicks(container);
}
async function renderJobs(container) {
  const data=await api('/api/jobs');
  container.innerHTML=`<div class="notice">A scheduled job is separate from the Telegram command listener. Removing jobs never deletes papers or notes. ${data.platform==='windows'?'Windows Task Scheduler is managed directly.':'The app is not running on Windows; remove also disables the job in app config, but you must remove any matching cron/launchd entry manually.'}</div><div class="job-list"><article class="job-card"><h3>Background scan</h3><span class="job-state">${data.scan_enabled?'Enabled in config':'Disabled in config'}</span><p>Collect new papers from configured topics. Runs while the web workspace is closed if the OS scheduler is configured.</p><button class="btn danger" data-remove-job="scan">Remove / disable scan</button></article><article class="job-card"><h3>Research digest</h3><span class="job-state">${data.digest_enabled?'Enabled in config':'Disabled in config'}</span><p>${esc(data.delivery?.frequency||'weekly')} at ${esc(data.delivery?.time||'09:00')}. Automatic delivery uses Telegram when configured.</p><button class="btn danger" data-remove-job="digest">Remove / disable digest</button></article></div><section class="panel" style="margin-top:15px"><div class="panel-head"><h2>Task scheduler</h2><button id="install-defaults" class="btn primary">Install default jobs</button></div><p class="muted">Default jobs: daily scan at 07:30 and Sunday digest at 09:00 local time. This UI installs the standard schedule as a pair; use the TUI/CLI to configure individual times.</p><p class="muted">${esc(data.note)}</p></section>`;
  container.querySelectorAll('[data-remove-job]').forEach(btn=>btn.addEventListener('click',async()=>{if(!confirm(`Remove scheduled ${btn.dataset.removeJob} job? Papers and config data will not be deleted.`))return;try{const result=await api(`/api/jobs/${btn.dataset.removeJob}/remove`,{method:'POST'});toast(result.message||'Job removed');renderJobs(container);}catch(e){toast(e.message,true);}}));
  $('#install-defaults',container).addEventListener('click',async()=>{try{await api('/api/jobs/install-defaults',{method:'POST'});toast('Default scan and digest jobs installed.');renderJobs(container);}catch(e){toast(e.message,true);}});
}
async function boot() { try { const health=await api('/api/health'); $('#connection').textContent=`${health.database} · connected`; } catch(e) { $('#connection').textContent='Connection error'; } renderPage(); }
boot();
