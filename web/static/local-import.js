/* Explicit uploaded-byte paper import. File contents live in memory only. */
(function(global){
  'use strict';
  const MAX_FILES=10,MAX_FILE=5000000,MAX_TOTAL=10000000;
  const views=new WeakMap();
  function render(root,context){
    if(!root)return;
    const {api,t,esc,state,onImported}=context;
    const s=state.localImport||(state.localImport={files:[],preview:null,selected:[],busy:false,open:false,message:null,result:null,revision:0});
    const tr=(key,values)=>t('li_'+key,values),$=selector=>root.querySelector(selector);
    const actionable=item=>['new','duplicate'].includes(item.status);
    const metadata=item=>{const data={...(item.metadata||{}),paper_id:item.paper_id},language=data.raw?.publication_language;return ['paper_id','doi','venue','published_at','authors','abstract'].filter(key=>data[key]).map(key=>`<p><strong>${tr('meta_'+key)}:</strong> ${esc(Array.isArray(data[key])?data[key].join(', '):data[key])}</p>`).join('')+`<p><strong>${tr('meta_publication_language')}:</strong> ${esc(language||tr('unknownLanguage'))}</p>`;};
    const fileLabel=()=>s.files.map(file=>file.filename).join(', ');
    const refresh=()=>views.get(state)?.draw();
    const reason=item=>tr('reason_'+(['new','duplicate','conflicting_metadata','invalid_file','invalid_metadata','missing_title'].includes(item.message_code)?item.message_code:'unknown'));
    views.set(state,{draw,imported:async()=>{await onImported?.();}});
    function draw(){
      root.innerHTML=`<details id="li-panel" ${s.open?'open':''}><summary>${tr('title')}</summary><p>${tr('help')}</p><p class="muted">${tr('limits')}</p><label for="li-files">${tr('files')}</label><input class="field" id="li-files" type="file" multiple accept=".ris,.bib,.bibtex,.pdf" ${s.busy?'disabled':''}><p id="li-selected-files">${esc(fileLabel()||tr('none'))}</p><div class="detail-actions"><button class="btn" id="li-preview" ${s.busy||!s.files.length?'disabled':''}>${tr(s.busy?'working':'preview')}</button><button class="btn" id="li-clear" ${s.busy?'disabled':''}>${tr('clear')}</button></div><p id="li-message" role="status" aria-live="polite" ${s.message?'':'hidden'}>${s.message?tr(s.message):''}</p>${s.result?`<p class="notice" id="li-success">${tr('success',{added:s.result.added??0,duplicates:s.result.duplicates??0})}</p>`:''}<div id="li-records"></div>${s.preview?`<p>${tr('reviewHelp')}</p><button class="btn primary" id="li-commit" ${s.busy||!s.selected.length?'disabled':''}>${tr('commit',{count:s.selected.length})}</button>`:''}</details>`;
      $('#li-panel').ontoggle=event=>{s.open=event.target.open;};
      if(s.preview){$('#li-records').innerHTML=(s.preview.items||[]).map(item=>`<article class="annotation-card"><p><span class="badge">${tr('status_'+(['new','duplicate','conflict','skipped','failed'].includes(item.status)?item.status:'failed'))}</span> ${esc(item.filename||'')}</p>${actionable(item)?`<label><input type="checkbox" data-import-index="${Number(item.index)}" ${s.selected.includes(item.index)?'checked':''} ${s.busy?'disabled':''}> ${esc(item.title||tr('untitled'))}</label>`:`<p>${esc(item.title||tr('untitled'))}</p>`}<p class="muted">${reason(item)}</p>${s.files.some(file=>file.filename===item.filename&&file.format==='pdf')?`<p class="notice">${tr('pdfHelp')}</p>`:''}${metadata(item)}</article>`).join('')||`<p>${tr('empty')}</p>`;root.querySelectorAll('[data-import-index]').forEach(box=>{box.onchange=()=>{const index=Number(box.dataset.importIndex);s.selected=s.selected.filter(value=>value!==index);if(box.checked)s.selected.push(index);$('#li-commit').disabled=s.busy||!s.selected.length;$('#li-commit').textContent=tr('commit',{count:s.selected.length});};});}
      $('#li-files').onchange=async event=>{
        const revision=++s.revision;const chosen=Array.from(event.target.files||[]);s.preview=null;s.selected=[];s.result=null;s.message=null;s.open=true;
        if(!chosen.length){s.files=[];draw();return;}
        if(chosen.length>MAX_FILES||chosen.some(file=>!file.size||file.size>MAX_FILE)||chosen.reduce((n,file)=>n+file.size,0)>MAX_TOTAL){s.files=[];s.message='invalid';draw();return;}
        s.busy=true;draw();
        try{
          const files=await Promise.all(chosen.map(async file=>{const extension=file.name.toLowerCase().split('.').pop();const format={ris:'ris',bib:'bibtex',bibtex:'bibtex',pdf:'pdf'}[extension];if(!format)throw new Error('format');const content_base64=await new Promise((resolve,reject)=>{const reader=new global.FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);});return {filename:file.name,format,content_base64};}));
          if(revision===s.revision)s.files=files;
        }catch(_){if(revision===s.revision){s.files=[];s.message='invalid';}}
        finally{if(revision===s.revision){s.busy=false;refresh();}}
      };
      $('#li-clear').onclick=()=>{s.revision++;s.files=[];s.preview=null;s.selected=[];s.result=null;s.message=null;draw();};
      $('#li-preview').onclick=()=>perform(false);
      if($('#li-commit'))$('#li-commit').onclick=()=>perform(true);
    }
    async function perform(commit){
      if(s.busy||!s.files.length||commit&&(!s.preview||!s.selected.length))return;
      const revision=s.revision;s.busy=true;s.message=null;s.open=true;draw();
      try{
        const payload={files:s.files};if(commit){payload.token=s.preview.token;payload.selected_indices=[...s.selected];}
        const result=await api('/api/local-import/'+(commit?'commit':'preview'),{method:'POST',body:JSON.stringify(payload)});
        if(revision!==s.revision)return;
        if(commit){s.result=result;s.preview=null;s.selected=[];await views.get(state)?.imported();}
        else {s.preview=result;s.selected=(result.items||[]).filter(actionable).map(item=>item.index);s.message=(result.items||[]).length?'review':'empty';}
      }catch(error){if(revision===s.revision){const status=error.detail?.status;s.message=status==='import_stale'?'stale':status==='import_parser'?'parser':status==='import_storage'?'storage':'invalid';if(status==='import_stale'){s.preview=null;s.selected=[];}}}
      finally{if(revision===s.revision){s.busy=false;refresh();}}
    }
    draw();
  }
  global.LocalBibliographyImport={render};
})(globalThis);
