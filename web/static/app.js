const state = { page: 'overview', papers: [], selected: null, query: '', status: 'all', sort: 'relevance_score', graphSeed: null, clusterData: null };
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
  const seed=state.graphSeed || state.selected?.id || null;
  const params=new URLSearchParams({depth:'1',max_nodes:'80'}); if(seed)params.set('seed_id',seed);
  const graph=await api(`/api/graph?${params}`);
  container.innerHTML=`<section class="panel"><div class="panel-head"><div><h2>Citation & related-work map</h2><p class="muted">Stored local relationships only · click a node to open the paper</p></div><button class="btn" id="refresh-graph">↻ Refresh map</button></div><div class="legend"><span><i class="dot seed"></i>Selected paper</span><span><i class="dot"></i>New / untriaged</span><span><i class="dot related"></i>Related work</span><span>→ citations are directed; dashed lines mean “related”</span></div><div class="svg-wrap"><svg id="graph-svg" class="graph-svg" viewBox="0 0 900 510" role="img" aria-label="Citation relationship graph"></svg></div><p class="muted">${graph.nodes.length} nodes · ${graph.edges.length} stored relationships${graph.truncated?' · node limit reached':''}. An empty map means this neighborhood has not been fetched into the local database yet; use Citation Discovery in CLI/TUI.</p><div id="graph-paper-list" class="paper-list">${graph.nodes.slice(0,8).map(paperRow).join('')}</div></section>`;
  $('#refresh-graph',container).addEventListener('click',()=>renderGraph(container)); bindPaperClicks(container); drawGraph(graph, $('#graph-svg',container));
}
function drawGraph(graph, svg) {
  const ns='http://www.w3.org/2000/svg', width=900, height=510; svg.innerHTML='';
  const make=(tag,attrs={})=>{const el=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,String(v)));return el;};
  if(!graph.nodes.length){const text=make('text',{x:450,y:245,'text-anchor':'middle',class:'node-label'});text.textContent='No papers in this graph yet';svg.append(text);return;}
  const centerIndex=graph.nodes.findIndex(p=>p.id===graph.seed_id); const center=Math.max(0,centerIndex); const positions=new Map(); positions.set(graph.nodes[center].id,{x:450,y:255});
  const others=graph.nodes.filter((_,i)=>i!==center); others.forEach((paper,i)=>{const angle=2*Math.PI*i/Math.max(others.length,1)-Math.PI/2;const radius=others.length<8?115:Math.min(210,100+others.length*3);positions.set(paper.id,{x:450+Math.cos(angle)*radius,y:255+Math.sin(angle)*radius*.78});});
  const edges=graph.edges; for(const edge of edges){const a=positions.get(Number(edge.source)),b=positions.get(Number(edge.target));if(!a||!b)continue;const line=make('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,class:`edge ${edge.type==='related'?'related':''}`});svg.append(line);if(edge.type==='cites'){const midX=(a.x+b.x)/2,midY=(a.y+b.y)/2;const mark=make('circle',{cx:midX,cy:midY,r:2,fill:'#8cc8f2'});svg.append(mark);}}
  for(const paper of graph.nodes){const pos=positions.get(paper.id);const group=make('g',{'data-node':paper.id,tabindex:0,role:'button','aria-label':titleOf(paper)});const classes=['node',paper.id===graph.seed_id?'seed':paper.status==='to-read'?'todo':paper.status==='read'?'read':'new'].join(' ');const circle=make('circle',{cx:pos.x,cy:pos.y,r:paper.id===graph.seed_id?16:scoreOf(paper)>.75?11:8,class:classes});group.append(circle);const label=make('text',{x:pos.x+14,y:pos.y+3,class:'node-label'});label.textContent=titleOf(paper).length>33?titleOf(paper).slice(0,31)+'…':titleOf(paper);group.append(label);group.addEventListener('click',()=>{state.graphSeed=paper.id;state.selected=paper;renderGraph($('#page-content'));});group.addEventListener('keydown',event=>{if(event.key==='Enter')group.dispatchEvent(new Event('click'));});svg.append(group);}
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
