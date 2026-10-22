const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const source=path.resolve(__dirname,'../../web/static');
const settle=async()=>{for(let n=0;n<12;n++)await new Promise(resolve=>setTimeout(resolve,2));};
function setup(t,language){
  const dom=new JSDOM('<section id="host"></section>',{url:'http://localhost:8765',runScripts:'outside-only'});t.after(()=>dom.window.close());
  const w=dom.window,state={},requests=[],mode={};let imported=0,root=w.document.querySelector('#host');
  for(const name of ['locales','local-import'])w.eval(fs.readFileSync(path.join(source,name+'.js'),'utf8'));
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const api=async(url,options)=>{const body=JSON.parse(options.body);requests.push({url,body});if(mode.delay)await new Promise(resolve=>{mode.resolve=resolve;});if(mode.error){const e=new Error('PRIVATE');e.detail={status:mode.error};throw e;}if(url.endsWith('/preview'))return {token:'a'.repeat(64),items:[{index:0,status:'new',message_code:'new',filename:'Наука.ris',title:'<img src=x onerror=evil()>',metadata:{abstract:'<script>unsafe</script>'}},{index:1,status:'duplicate',message_code:'duplicate',filename:'Наука.ris',title:'Existing'},{index:2,status:'conflict',message_code:'conflicting_metadata',filename:'Наука.ris',title:'Conflict'}]};return {added:1,duplicates:1,batch_id:'test'};};
  function draw(locale=language){w.LocalBibliographyImport.render(root,{api,t:(k,v)=>w.LitI18n.translate(locale,k,v),esc,state,onImported:async()=>{imported++;}});}
  async function choose(name='Наука.ris',text='TY  - JOUR\nTI  - Test\nER  -\n'){const input=root.querySelector('#li-files');Object.defineProperty(input,'files',{value:[new w.File([text],name)]});input.dispatchEvent(new w.Event('change'));await settle();}
  function navigate(locale){const next=w.document.createElement('section');root.replaceWith(next);root=next;draw(locale);}
  draw();return {w,get root(){return root;},state,requests,mode,draw,navigate,choose,$:selector=>root.querySelector(selector),get imported(){return imported;}};
}
for(const language of ['en','uk'])test(`explicit bibliography preview, safe records and selected commit (${language})`,async t=>{
  const ctx=setup(t,language),{$,requests}=ctx;
  assert.equal(requests.length,0);assert.equal($('#li-preview').disabled,true);
  await ctx.choose();assert.equal(requests.length,0);assert.ok($('#li-selected-files').textContent.includes('Наука.ris'));
  $('#li-preview').click();await settle();assert.equal(requests.length,1);assert.equal(requests[0].url,'/api/local-import/preview');
  assert.equal($('#li-records img'),null);assert.equal($('#li-records script'),null);assert.ok($('#li-records').textContent.includes('<img'));
  assert.equal(ctx.root.querySelectorAll('[data-import-index]').length,2);
  assert.ok($('#li-records').textContent.includes(language==='uk'?'Невідомо (не визначається автоматично)':'Unknown (not inferred)'));
  const duplicate=$('[data-import-index="1"]');duplicate.checked=false;duplicate.dispatchEvent(new ctx.w.Event('change'));
  $('#li-commit').click();await settle();assert.deepEqual(requests[1].body.selected_indices,[0]);assert.equal(ctx.imported,1);assert.ok($('#li-success'));assert.equal($('#li-commit'),null);
});
test('file data and preview selection survive locale and navigation; stale retains files',async t=>{
  const ctx=setup(t,'en'),{$,requests}=ctx;await ctx.choose();$('#li-preview').click();await settle();
  const zero=$('[data-import-index="0"]');zero.checked=false;zero.dispatchEvent(new ctx.w.Event('change'));
  ctx.draw('uk');assert.equal($('[data-import-index="0"]').checked,false);assert.ok($('#li-selected-files').textContent.includes('Наука.ris'));assert.equal(requests.length,1);
  ctx.mode.error='import_stale';$('#li-commit').click();await settle();assert.equal($('#li-commit'),null);assert.ok($('#li-message').textContent.includes('змінилися'));assert.ok($('#li-selected-files').textContent.includes('Наука.ris'));assert.equal($('#li-preview').disabled,false);
  ctx.draw('en');assert.equal(requests.length,2);assert.ok($('#li-message').textContent.includes('changed'));
});
test('changing selected files invalidates preview, unsupported file stays local',async t=>{
  const ctx=setup(t,'en'),{$,requests}=ctx;await ctx.choose();$('#li-preview').click();await settle();
  await ctx.choose('Other.ris');assert.equal($('#li-commit'),null);assert.equal(requests.length,1);
  await ctx.choose('archive.zip');assert.equal($('#li-preview').disabled,true);assert.equal(requests.length,1);assert.ok($('#li-message').textContent.includes('formats'));
});

test('pending preview and commit refresh the active view after navigation and locale change',async t=>{
  const ctx=setup(t,'en'),{$}=ctx;await ctx.choose();
  ctx.mode.delay=true;$('#li-preview').click();ctx.navigate('uk');
  assert.equal($('#li-preview').disabled,true);assert.ok($('#li-preview').textContent.includes('Обробка'));
  ctx.mode.resolve();await settle();
  assert.equal($('#li-preview').disabled,false);assert.ok($('#li-records').textContent.includes('Новий бібліографічний запис'));
  $('#li-commit').click();ctx.navigate('en');assert.equal($('#li-preview').disabled,true);
  ctx.mode.resolve();await settle();assert.equal(ctx.imported,1);assert.ok($('#li-success').textContent.includes('Import saved'));assert.equal($('#li-preview').disabled,false);
});
for(const status of ['import_parser','import_storage','unknown'])test(`safe ${status} error preserves file selection`,async t=>{
  const ctx=setup(t,'uk'),{$}=ctx;await ctx.choose();ctx.mode.error=status;$('#li-preview').click();await settle();
  assert.ok($('#li-message').textContent.length>5);assert.ok(!$('#li-message').textContent.includes('PRIVATE'));
  assert.ok($('#li-selected-files').textContent.includes('Наука.ris'));assert.equal($('#li-preview').disabled,false);
});
