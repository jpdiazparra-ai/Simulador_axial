// The dashboard can be standalone or nested in two Streamlit frames.
// Mount in the highest accessible document so the control stays in the viewport.
function pageRefreshWindows(start=window){
 const frames=[start];let current=start;
 while(current.parent&&current.parent!==current){try{const parent=current.parent;void parent.document.body;frames.push(parent);current=parent;}catch{break;}}
 return frames;
}
function pageRefreshCapture(frames){
 const local=frames[0],doc=local.document;
 const anchor=[...doc.querySelectorAll('.sequence-step[id]')].filter(node=>node.getBoundingClientRect().top<=24).at(-1);
 return {version:1,savedAt:Date.now(),frames:frames.map(frame=>({x:frame.scrollX||0,y:frame.scrollY||0,main:frame.document.querySelector('[data-testid="stMain"]')?.scrollTop??null})),
  anchor:anchor?{id:anchor.id,top:anchor.getBoundingClientRect().top}:null,
  details:[...doc.querySelectorAll('details[data-preserve]')].map(node=>node.open),
  sourceKey:typeof CostPreview!=='undefined'?CostPreview.sourceKey:null};
}
function pageRefreshRestore(frames,state){
 if(state?.version!==1||!Array.isArray(state.frames))return;
 const doc=frames[0].document;
 [...doc.querySelectorAll('details[data-preserve]')].forEach((node,index)=>{if(typeof state.details?.[index]==='boolean')node.open=state.details[index];});
 frames.forEach((frame,index)=>{const saved=state.frames[index];if(!saved)return;
  if(Number.isFinite(saved.x)&&Number.isFinite(saved.y))frame.scrollTo(saved.x,saved.y);
  const main=frame.document.querySelector('[data-testid="stMain"]');if(main&&Number.isFinite(saved.main))main.scrollTop=saved.main;
 });
 const anchor=state.anchor&&doc.getElementById(state.anchor.id);if(anchor&&Number.isFinite(state.anchor.top))frames[0].scrollTo(state.frames[0].x,frames[0].scrollY+anchor.getBoundingClientRect().top-state.anchor.top);
}
function initPageRefresh(){
 const frames=pageRefreshWindows(),host=frames.at(-1),doc=host.document,key='vawt-page-refresh-v1:'+host.location.pathname;
 const old=doc.getElementById('vawt-page-refresh');if(old)old.remove();
 if(!doc.getElementById('vawt-page-refresh-style')){const style=doc.createElement('style');style.id='vawt-page-refresh-style';style.textContent=`
 #vawt-page-refresh{position:fixed;right:max(18px,env(safe-area-inset-right));bottom:max(18px,env(safe-area-inset-bottom));z-index:999999;display:inline-flex;align-items:center;gap:8px;padding:10px 15px;min-height:40px;border:1px solid #dce4de;border-radius:9px;background:#fffffff5;color:#254e3d;font:600 12px/1.2 system-ui,-apple-system,sans-serif;box-shadow:0 3px 14px #203d2c12;cursor:pointer;backdrop-filter:blur(8px);transition:background .15s,box-shadow .15s}
 #vawt-page-refresh:hover{background:#f2f7f4;box-shadow:0 4px 18px #203d2c20}#vawt-page-refresh:focus-visible{outline:2px solid #467761;outline-offset:3px}#vawt-page-refresh:disabled{opacity:.65;cursor:wait}#vawt-page-refresh svg{width:16px;height:16px;flex:none}
 @media print{#vawt-page-refresh{display:none}}`;doc.head.append(style);}
 const button=doc.createElement('button');button.id='vawt-page-refresh';button.type='button';button.title='Actualizar la página y conservar tu ubicación';button.setAttribute('aria-label',button.title);
 // Constant markup; no model or spreadsheet content enters this HTML.
 button.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 6.1A8 8 0 0 1 20 12M4 12a8 8 0 0 0 13.9 5.9"/></svg><span>Actualizar</span>';
 button.onclick=()=>{
  try{if(typeof costSave==='function')costSave();if(typeof IFCView!=='undefined'&&IFCView.storageKey)sessionStorage.setItem(IFCView.storageKey,JSON.stringify(captureIfcViewState()));host.sessionStorage.setItem(key,JSON.stringify(pageRefreshCapture(frames)));}catch{}
  button.disabled=true;button.querySelector('span').textContent='Actualizando…';host.location.reload();
 };
 doc.body.append(button);
 let state;try{state=JSON.parse(host.sessionStorage.getItem(key));host.sessionStorage.removeItem(key);}catch{}
 if(state?.version!==1||!Number.isFinite(state.savedAt)||Date.now()-state.savedAt>120000)return;
 if(state.sourceKey&&typeof CostPreview!=='undefined'){CostPreview.sourceKey=state.sourceKey;updateCostPreview();}
 let cancelled=false;const timers=[];
 const stop=()=>{cancelled=true;timers.forEach(clearTimeout);for(const frame of frames)for(const type of ['wheel','touchstart','pointerdown','keydown'])frame.removeEventListener(type,stop,true);};
 for(const frame of frames)for(const type of ['wheel','touchstart','pointerdown','keydown'])frame.addEventListener(type,stop,{capture:true,passive:true});
 const restore=()=>{if(!cancelled)pageRefreshRestore(frames,state);};
 // The wrapper restores its own scroll on load; run after it and after frame sizing.
 requestAnimationFrame(()=>requestAnimationFrame(restore));
 for(const delay of [120,400,1000])timers.push(setTimeout(restore,delay));timers.push(setTimeout(stop,1300));
}
