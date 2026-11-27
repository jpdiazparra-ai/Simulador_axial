// Offline report of point 6. Keep the chart's layer scope and the table's package scope explicit.
function costExportEscape(value){return String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));}
function costAnalysisSnapshot(){
 const state=captureCostViewState(),table=costFilteredRows(),context=costChartRows(),board=costBoardData(context);
 return {generatedAt:new Date().toISOString(),state,variant:IFCView.offer,title:typeof document==='undefined'||typeof document.getElementById!=='function'?null:document.getElementById('cost-section-title')?.textContent,modelLayers:IFCView.data?.layers||[],model:{metadata:IFCView.data?.metadata||{},layers:IFCView.data?.layers||[],meshes:typeof costPreviewProducts==='function'&&IFCView.data?.meshes?costPreviewProducts(IFCView.data,CostView,IFCView.offer):[]},contextRows:context.map(row=>({...row})),tableRows:table.map(row=>({...row})),tableStats:costStats(table),contextCount:context.length,assembly:costAssemblySummary(context),
  board:{...board,groups:board.groups.map(group=>({key:group.key,name:group.name,count:group.rows.length,stats:{...group.stats}}))},
  source:{...CostView.data.metadata},component:CostPreview.sourceKey||null};
}
function costExportBoardRows(snapshot){
 const {board,state}=snapshot,span=board.maximum-board.minimum||1,e=costExportEscape;
 const money=value=>value===null?'Sin dato':'US$ '+f(value/state.fxRate,2);
 return board.groups.map((group,index)=>{
  const comparisons=['current','previous'].map(key=>{const amount=group.stats[key],known=group.stats[key+'Count']>0,left=(Math.min(0,amount)-board.minimum)/span*100,width=Math.abs(amount)/span*100;
   return '<span class="cost-board-series '+key+'"><span class="cost-board-track"><i class="cost-board-zero" style="left:'+(-board.minimum/span*100)+'%"></i>'+(known&&amount!==0?'<i class="cost-board-fill" style="left:'+left+'%;width:'+width+'%"></i>':'')+'</span><strong>'+e(money(known?amount:null))+'</strong></span>';
  }).join('');
  const share=group.stats[board.base+'Count']&&board.positive>0&&group.stats[board.base]>=0?f(group.stats[board.base]/board.positive*100,1)+' %':'—';
  return '<div class="cost-board-row"><span class="cost-board-name"><span class="cost-board-rank">'+String(index+1).padStart(2,'0')+'</span><strong>'+e(group.name)+'</strong><small>'+group.count+' partidas</small></span><span class="cost-board-comparison">'+comparisons+'</span><span class="cost-board-share"><strong>'+e(share)+'</strong><small>participación</small></span></div>';
 }).join('');
}
// Export controls keep their nested label, value, and note elements.
function costExportFreezeButtons(section,doc=document){
 for(const button of [...section.querySelectorAll('button')]){if(['cost-chart-back','cost-preview-reset','cost-preview-open'].includes(button.id))continue;const replacement=doc.createElement(button.classList.contains('cost-kpi')?'div':'span');replacement.className=button.className;replacement.append(...button.childNodes);button.replaceWith(replacement);}
}
// Native scrolling only: no wheel or pointer handler captures the table's gestures.
function initCostExportTableViewport(doc=document){
 const table=doc.getElementById('cost-table'),wrap=table?.closest('.cost-table-wrap');if(!table||!wrap)return;
 wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Partidas que componen la selección. Desplazamiento horizontal y vertical; encabezado, totales y columnas de los extremos fijos.');
}
function costExportVisualSource(){
 if(typeof makeIfcProductMesh!=='function')return '';
 return [modelSourceText,modelDisplayName,decodeIfcMesh,makeIfcProductMesh,modelGroupKey,modelWeightKg,modelGroupQuantity,modelUnitWeight,modelWeightGroups,modelAssemblyMasses,renderModelWeights,costPreviewProducts,updateCostPreview,fitCostPreview,renderCostPreview,costPreviewSize,createCostPreview,initCostPreview].map(fn=>fn.toString()).join('\n');
}
function costExportDocument(snapshot,styles,sectionHtml){
 const dockCss=typeof costDockStyles==='function'?costDockStyles():'';
 const e=costExportEscape,s=snapshot.state,scope=[s.milestone==='all'?'Todos los hitos':s.milestone,s.layer==='all'?(s.modelSelectionActive&&!(s.selectedLayers||[]).length?'Sin capas seleccionadas':(s.selectedLayers||[]).length?'Capas: '+s.selectedLayers.join(' · '):'Todas las capas'):s.layer,s.package==='all'?'Todos los paquetes':s.package,s.activity==='all'?null:'Actividad '+s.activity,s.search?'Búsqueda: '+s.search:null].filter(Boolean).join(' · ');
 const stamp=new Date(snapshot.generatedAt).toLocaleString('es-CL',{dateStyle:'medium',timeStyle:'short'});
 const json=JSON.stringify(snapshot).replaceAll('<','\\u003c').replaceAll('>','\\u003e').replaceAll('&','\\u0026');
 const engine=typeof COST_EXPORT_ENGINE==='string'?COST_EXPORT_ENGINE:'';
 const three=typeof document!=='undefined'&&typeof document.getElementById==='function'?(document.getElementById('three-library')?.textContent||''):'';
 const safeThree=three.replace(/<\/script/gi,'<\\/script');
 const prelude="const $=id=>document.getElementById(id);const f=(v,n=1)=>Number.isFinite(v)?v.toLocaleString('es-CL',{minimumFractionDigits:n,maximumFractionDigits:n}):'—';function element(tag,attrs={},content=''){const e=document.createElement(tag);Object.assign(e,attrs);e.textContent=content;return e;}const offlineData=JSON.parse($('cost-analysis-snapshot').textContent);const IFCView={offer:offlineData.variant,data:offlineData.model||{layers:offlineData.modelLayers||[],meshes:[]}};const CostPreview={ready:false,visible:false,layer:null,dirty:true};function navigateToStep(){}";
 const runtime=(prelude+'\n'+engine+'\n'+costExportVisualSource()+'\n'+initCostExportTableViewport.toString()+'\n('+initCostOfflineReport.toString()+')();').replace(/<\/script/gi,'<\\/script');
 return '<!doctype html><html lang="es" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Costos de la turbina · análisis</title><style>'+styles+dockCss+'\n'+
 'body{background:#f3f4f2}.cost-export-page{max-width:1900px;margin:auto;padding:24px}.cost-export-heading{padding:20px 24px;background:var(--surface);border:1px solid var(--line);border-radius:12px;margin-bottom:16px}.cost-export-heading h1{font-size:25px;margin:0 0 8px}.cost-export-heading p{font-size:12px;line-height:1.7;color:var(--ink2);margin:4px 0}.cost-export-caption{padding:12px;font-size:11px;color:var(--ink2)}.cost-export-image{display:block;width:100%;height:100%;object-fit:contain;background:#eaf0f4}.cost-export-page #cost-preview-viewport{position:relative}.cost-export-page .cost-controls,.cost-export-page #cost-preview-open,.cost-export-page .cost-kpi-action{display:none!important}.cost-export-page .cost-board-row{cursor:pointer}.cost-export-page .cost-offline-navigation{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 10px;font-size:11px;color:var(--ink2)}.cost-export-page .cost-offline-navigation .btn{font-size:10px;padding:5px 8px}.cost-export-page .cost-donut-switch{gap:6px}.cost-export-page .cost-donut-switch button{padding:5px 8px}.cost-export-page .cost-chart-card #cost-chart-hint{display:none}.cost-export-page .cost-metrics .cost-kpi{display:flex;flex-direction:column;align-items:flex-start;min-width:0;box-sizing:border-box}.cost-export-page .cost-kpi :is(.cost-kpi-tag,.cost-kpi-label,strong,small){display:block;width:100%}.cost-export-page .cost-table-wrap{position:relative;isolation:isolate;max-height:min(70vh,650px);overflow:auto;overscroll-behavior:auto;scrollbar-width:auto;scrollbar-gutter:stable;touch-action:pan-x pan-y;cursor:auto}.cost-export-page #cost-table{border-collapse:separate;border-spacing:0}.cost-export-page #cost-table thead th{position:sticky;top:0;z-index:4;background:var(--cost-soft);box-shadow:0 1px 0 var(--cost-border)}.cost-export-page #cost-table tfoot td{position:sticky;bottom:0;z-index:4;background:var(--cost-soft);box-shadow:0 -1px 0 var(--cost-border)}.cost-export-page #cost-table tbody td:first-child{position:sticky;left:0;z-index:2;background:var(--surface);box-shadow:3px 0 8px #23354b0a}.cost-export-page #cost-table tbody td:last-child{position:sticky;right:0;z-index:2;background:var(--surface);box-shadow:-3px 0 8px #23354b0a}.cost-export-page #cost-table thead th:first-child,.cost-export-page #cost-table tfoot td:first-child{position:sticky;left:0;z-index:6;background:var(--cost-soft)}.cost-export-page #cost-table thead th:last-child,.cost-export-page #cost-table tfoot td:last-child{position:sticky;right:0;z-index:6;background:var(--cost-soft)}.cost-export-page .cost-crumb{display:inline-block}.cost-export-page .cost-fx-control>span{display:block}.cost-export-page .cost-fx-value{font-size:16px;font-weight:650}.cost-export-page select{max-width:100%}@media(max-width:600px){.cost-export-page{padding:10px}}@media print{@page{size:A3 landscape;margin:12mm}.cost-export-page{max-width:none;padding:0}.cost-export-page .cost-focus-layout{display:block}.cost-export-page :is(.cost-chart-card,.cost-preview-card,.cost-weights-card){height:auto!important;margin-bottom:12px;break-inside:avoid}.cost-export-page :is(#cost-layer-chart,.model-weight-scroll,.cost-board-rows,.cost-table-wrap){overflow:visible!important;max-height:none!important}.cost-export-page .cost-preview-card #cost-preview-viewport{height:300px!important;flex:none}.cost-export-page .model-weight-scroll{flex:none}#cost-table{min-width:0;font-size:8px}#cost-table :is(th,td){padding:5px;min-width:0!important;position:static!important}}'+
 '</style></head><body><main class="cost-export-page"><header class="cost-export-heading"><h1>Costos de la turbina · análisis</h1><p>'+e(scope)+'</p><p>'+snapshot.tableRows.length+' partidas en la tabla · '+snapshot.contextCount+' partidas en los indicadores y el gráfico de contexto · USD · 1 USD = '+e(f(s.fxRate,2))+' CLP · '+e(snapshot.model?.metadata?.label||('Modelo V5 '+snapshot.variant))+'</p><p>Generado '+e(stamp)+'. Geometría 3D y pesos sincronizados con la selección, disponibles sin conexión. Pesos declarados del archivo, separados de los kg de Costos.</p></header>'+sectionHtml+'</main><script id="cost-analysis-snapshot" type="application/json">'+json+'</'+'script><script>'+safeThree+'</'+'script><script>'+runtime+'</'+'script></body></html>';
}
function downloadCostAnalysisHtml(){
 const snapshot=costAnalysisSnapshot(),section=$('step-6').cloneNode(true);
 const originals=[...$('step-6').querySelectorAll('select,input')];[...section.querySelectorAll('select,input')].forEach((control,index)=>{control.value=originals[index].value;});
 // The rendered table already contains every filtered row, including subtotals.
 section.querySelector('.cost-controls')?.remove();
 for(const selector of ['#cost-export-html','#cost-refresh','#cost-reset-mapping','#cost-layer-selection'])section.querySelector(selector)?.remove();
 const rows=section.querySelector('.cost-board-rows');if(rows){rows.innerHTML=costExportBoardRows(snapshot);const bottom=section.querySelector('.cost-board-bottom');if(bottom)bottom.textContent=snapshot.board.groups.length+' categorías completas · orden por '+(snapshot.board.base==='current'?'costo al detalle':'costo por mayor')+(snapshot.state.package!=='all'?' · Tabla filtrada por: '+snapshot.state.package:'');}
 const viewport=section.querySelector('#cost-preview-viewport');if(viewport){
  const canvas=element('canvas',{id:'cost-preview-canvas',tabIndex:0,ariaLabel:'Modelo 3D de las capas seleccionadas'}),empty=element('div',{id:'cost-preview-empty',hidden:true}),tools=element('div',{id:'cost-preview-tools'});
  tools.append(element('button',{id:'cost-preview-reset',type:'button',className:'btn'},'Centrar'),element('span',{},'Arrastra para girar · Rueda: zoom'));viewport.replaceChildren(canvas,empty,tools);
 }
 // Replace live controls with their displayed value; native details remain expandable.
 for(const control of [...section.querySelectorAll('select,input')]){const original=$(control.id),value=original?.value??control.value,span=document.createElement('span');span.className='cost-fx-value';span.textContent=control.tagName==='SELECT'?(control.options[control.selectedIndex]?.textContent||value):value;control.replaceWith(span);}
 costExportFreezeButtons(section);
 const styles=[...document.querySelectorAll('style')].map(style=>style.textContent).join('\n');
 download('costos_turbina_'+(snapshot.state.layer==='all'&&!snapshot.state.modelSelectionActive&&!(snapshot.state.selectedLayers||[]).length&&snapshot.state.package==='all'&&snapshot.state.activity==='all'&&!snapshot.state.search?'total':'seleccion')+'.html',costExportDocument(snapshot,styles,section.outerHTML),'text/html;charset=utf-8');
}

// Reuse the live financial engine with an offline-only renderer and a fixed exported scope.
function initCostOfflineReport(){
 const snapshot=JSON.parse($('cost-analysis-snapshot').textContent),initial=structuredClone(snapshot.state),context=snapshot.contextRows||snapshot.tableRows;
 Object.assign(CostView,initial,{data:{metadata:snapshot.source,rows:context},mapping:{...initial.mapping}});
 costSave=()=>{};
 for(const id of ['cost-layer','cost-search'])if(!$(id)){const input=document.createElement('input');input.id=id;input.hidden=true;document.body.append(input);}
 const navigation=document.createElement('div');navigation.className='cost-offline-navigation';const reset=element('button',{type:'button',className:'btn'},'↶ Restablecer informe'),label=element('span');navigation.append(reset,label);$('cost-metrics').before(navigation);
 reset.onclick=()=>{Object.assign(CostView,structuredClone(initial),{package:'all',activity:'all'});renderCostDashboard();};
 const dock=element('nav',{id:'vawt-cost-dock',ariaLabel:'Aislar conjuntos del informe exportado'});dock.dataset.collapsed=String(innerWidth<700);
 const toggle=element('button',{type:'button',className:'cost-dock-toggle',ariaExpanded:String(innerWidth>=700)},innerWidth<700?'Conjuntos ›':'‹ Conjuntos');toggle.onclick=()=>{const collapsed=dock.dataset.collapsed!=='true';dock.dataset.collapsed=String(collapsed);toggle.textContent=collapsed?'Conjuntos ›':'‹ Conjuntos';toggle.setAttribute('aria-expanded',String(!collapsed));};dock.append(toggle);
 for(const [group,text]of [['rotor','Aislar rotor'],['tower','Aislar torre'],['foundation','Aislar fundación y morteros'],['all','Restablecer']]){
  const button=element('button',{type:'button',className:'cost-dock-action'},text);button.dataset.group=group;
  const names=[...new Set([...context.map(costLayer),...(snapshot.model?.meshes||[]).map(product=>product.layer)].filter(name=>turbineLayerGroup(name)===group))];
  button.disabled=group!=='all'&&!names.length;if(button.disabled)button.title='Este conjunto no está incluido en el alcance exportado';
  button.onclick=()=>{if(group==='all'){reset.click();return;}const selected=costToggleDockGroup(costDockGroups(),group),layers=[...new Set([...context.map(costLayer),...(snapshot.model?.meshes||[]).map(product=>product.layer)].filter(name=>selected.includes(turbineLayerGroup(name))))];Object.assign(CostView,{selectedLayers:layers,modelSelectionActive:true,layer:layers.length===1?layers[0]:'all',package:'all',activity:'all',search:''});renderCostDashboard();};dock.append(button);
 }
 document.body.append(dock);
 const visualReady=typeof updateCostPreview==='function'&&typeof THREE!=='undefined';
 if(visualReady){CostPreview.sourceKey=snapshot.component;CostPreview.weightScope=CostView.layer+'::'+(CostView.selectedLayers||[]).slice().sort().join('|')+'::'+IFCView.offer;}
 navigateToStep=()=>{};
 renderCostDashboard=()=>{
  const rows=costFilteredRows(),chartRows=costChartRows();renderCostTrace(chartRows);
  renderCostKpis(chartRows,costStats(chartRows));renderCostAssemblyKpis(chartRows);renderCostLayers(chartRows);renderCostTable(rows);
  $('cost-table-count').textContent=rows.length+' partidas · USD';$('cost-empty').hidden=rows.length>0;
  label.textContent=(CostView.layer==='all'?'Alcance exportado':CostView.layer)+(CostView.package!=='all'?' › '+CostView.package:'')+' · '+rows.length+' partidas';
  for(const button of document.querySelectorAll('#cost-table .cost-layer-cell button'))button.remove();
  for(const select of document.querySelectorAll('#cost-table select')){const text=element('span',{},select.options[select.selectedIndex]?.textContent||'Sin capa asignada');select.replaceWith(text);}
  const selected=costDockGroups();for(const button of dock.querySelectorAll('[data-group]'))button.setAttribute('aria-pressed',String(button.dataset.group==='all'?selected===null:!!selected?.includes(button.dataset.group)));
  if(visualReady)updateCostPreview();
  initCostExportTableViewport();
 };
 renderCostDashboard();
 if(visualReady)initCostPreview();
}
