(function(root) {
  'use strict';
  function bindNoteHistory(container,{api,t,confirm,onRestored,onError}) {
    container.querySelectorAll('[data-restore-note]').forEach(button=>button.onclick=async()=>{
      if(!confirm(t('restoreNoteConfirm')))return;
      button.disabled=true;const notes=container.closest('#detail-panel').querySelector('#detail-notes');
      if(notes)notes.readOnly=true;
      try {
        const id=container.closest('#detail-panel').querySelector('#note-provenance').dataset.noteId;
        const paper=await api(`/api/papers/${button.dataset.paper}/notes/history/${button.dataset.restoreNote}/restore`,
          {method:'POST',body:JSON.stringify({expected_note_id:id?Number(id):null})});
        onRestored(paper,container.isConnected);
      } catch(e){onError(e);} finally{button.disabled=false;if(notes)notes.readOnly=false;}
    });
  }
  function bindCards(list,items,{api,t,esc,confirm,reload,onError,clearEdit}) {
    for(const item of items) {
      const card=list.querySelector(`[data-annotation="${item.id}"]`);if(!card||card.querySelector('[data-recovery]'))continue;
      if(item.deleted_at)card.querySelectorAll('[data-edit],[data-review],.annotation-editor').forEach(el=>el.hidden=true);
      const actions=card.querySelector('.detail-actions');
      const action=card.ownerDocument.createElement('button');action.className=item.deleted_at?'btn':'btn danger';
      action.textContent=t(item.deleted_at?'restoreAnnotation':'deleteAnnotation');
      action.dataset.recovery=String(item.id);actions.append(action);
      action.onclick=async()=>{
        if(!confirm(t(item.deleted_at?'restoreAnnotationConfirm':'deleteAnnotationConfirm')))return;
        action.disabled=true;
        try {
          await api(`/api/papers/${item.paper_id}/annotations/${item.id}${item.deleted_at?'/restore':''}`,
            {method:item.deleted_at?'POST':'DELETE',body:JSON.stringify({expected_revision:item.revision})});
          if(item.deleted_at)clearEdit(item.id);
          await reload();
        }catch(e){onError(e);}finally{action.disabled=false;}
      };
      const history=card.ownerDocument.createElement('details');
      history.innerHTML=`<summary>${t('annotationHistory')}</summary><div class="version-list"></div><button class="btn history-more" hidden>${t('older')}</button>`;
      card.append(history);let cursor=null,loaded=false;
      async function load(append=false) {
        const target=history.querySelector('.version-list'),more=history.querySelector('.history-more');more.disabled=true;
        try {
          const data=await api(`/api/papers/${item.paper_id}/annotations/${item.id}/history?limit=20${append&&cursor?'&before_revision='+cursor:''}`);
          const html=data.items.map(v=>`<article class="annotation-card"><p class="muted">${t('revision',{revision:v.revision})} · ${esc(v.recorded_at)}${v.deleted_at?' · '+t('deleted'):''}</p><p class="annotation-content">${esc(v.content)}</p><button class="btn" data-restore-revision="${v.revision}">${t('restoreVersion')}</button></article>`).join('');
          if(append)target.insertAdjacentHTML('beforeend',html);else target.innerHTML=html;
          cursor=data.next_before_revision;more.hidden=!cursor;loaded=true;
          target.querySelectorAll('[data-restore-revision]').forEach(button=>button.onclick=async()=>{
            if(!confirm(t('restoreAnnotationConfirm')))return;button.disabled=true;
            try {
              await api(`/api/papers/${item.paper_id}/annotations/${item.id}/restore`,{method:'POST',body:JSON.stringify({expected_revision:item.revision,restore_revision:Number(button.dataset.restoreRevision)})});
              clearEdit(item.id);await reload();
            }catch(e){onError(e);}finally{button.disabled=false;}
          });
        }catch(e){onError(e);}finally{more.disabled=false;}
      }
      history.ontoggle=()=>{if(history.open&&!loaded)load();};history.querySelector('.history-more').onclick=()=>load(true);
    }
  }
  function attach(section,paperId,{api,t,esc,reload,onError,onSuccess=()=>{}}) {
    const doc=section.ownerDocument;
    const tools=doc.createElement('details');tools.className='inference-tools';
    tools.innerHTML=`<summary>${t('freshInference')}</summary><p class="muted">${t('inferenceHelp')}</p><div class="detail-fields"><label>${t('llmProvider')}<select id="llm-provider" class="field" disabled></select></label><label>${t('model')}<input id="llm-model" class="field" maxlength="120"></label><label><input id="llm-consent" type="checkbox"> ${t('inferenceConsent')}</label><button id="generate-annotation" class="btn primary" disabled>${t('generateFresh')}</button></div>`;
    section.querySelector('#annotation-form').before(tools);
    const select=tools.querySelector('select'),model=tools.querySelector('#llm-model'),consent=tools.querySelector('#llm-consent'),generate=tools.querySelector('button');
    let providers=[];
    api('/api/annotation-adapters').then(data=>{
      providers=data.providers;select.innerHTML=providers.map(p=>`<option value="${esc(p.id)}" ${p.available?'':'disabled'}>${esc(p.id)}${p.available?'':' · '+t('unavailable')}</option>`).join('');
      const first=providers.find(p=>p.available);select.disabled=!first;
      if(first){select.value=first.id;model.value=first.model;}
      generate.disabled=!first||!consent.checked;
    }).catch(onError);
    select.onchange=()=>{model.value=providers.find(p=>p.id===select.value)?.model||'';consent.checked=false;generate.disabled=true;};
    model.oninput=()=>{consent.checked=false;generate.disabled=true;};
    consent.onchange=()=>{generate.disabled=select.disabled||!consent.checked;};
    generate.onclick=async()=>{
      if(!consent.checked||select.disabled)return;generate.disabled=true;
      try {
        const result=await api(`/api/papers/${paperId}/annotations/generate`,{method:'POST',body:JSON.stringify({provider:select.value,model:model.value||null,consent:true,language:doc.documentElement.lang})});
        consent.checked=false;await reload();onSuccess(result);
      }catch(e){onError(e);}finally{generate.disabled=!consent.checked||select.disabled;}
    };
    const input=section.querySelector('#annotation-import');input.multiple=true;input.accept='.json,.ris,.bib,.bibtex,.pdf';
    input.onchange=async()=>{
      const files=[...input.files];if(!files.length)return;input.disabled=true;
      try {
        if(files.length>10||files.reduce((sum,f)=>sum+f.size,0)>5000000)throw new Error(t('fileLimit'));
        const encoded=[];
        for(const file of files) {
          const suffix=file.name.split('.').pop().toLowerCase(),format={json:'json',ris:'ris',bib:'bibtex',bibtex:'bibtex',pdf:'pdf'}[suffix];
          if(!format)throw new Error(t('unsupportedFile'));
          const content_base64=await new Promise((resolve,reject)=>{const reader=new doc.defaultView.FileReader();reader.onerror=()=>reject(new Error(t('invalidImport')));reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.readAsDataURL(file);});
          encoded.push({filename:file.name,format,content_base64});
        }
        const result=await api(`/api/papers/${paperId}/annotations/import-files`,{method:'POST',body:JSON.stringify({files:encoded})});
        await reload();onSuccess(result);
      }catch(e){onError(e);}finally{input.value='';input.disabled=false;}
    };
  }
  const api={attach,bindCards,bindNoteHistory};root.AnnotationWorkflows=api;
  if(typeof module!=='undefined')module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
