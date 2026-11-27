// V80 v5 geometry is independent of the aerodynamic study. Z is the original vertical axis.
const IFCView={offer:'A',ready:false,visible:false,play:!matchMedia('(prefers-reduced-motion: reduce)').matches,rpm:30,scale:.2,follow:false,angle:0,layers:new Map(),meshes:[],dirty:true};
function updateIfcAnalysisContext(){
 if(!$('ifc-scope'))return;
 $('ifc-scope').textContent='Geometría V80 v5: D14 × H14 m · Análisis actual: D'+f(D.diameter??D.params?.D??12,1)+' × H'+f(D.height,1)+' m. El visor conserva las dimensiones del archivo; sus resultados energéticos no se recalculan aquí.';
 if(IFCView.follow){IFCView.rpm=Number.isFinite(sample().rpm)?sample().rpm:0;IFCView.dirty=true;}
 ifcMotionLabels();
}
function ifcMotionLabels(){const v=IFCView;$('ifc-play').textContent=v.play?'Pausar':'Reproducir';$('ifc-play').setAttribute('aria-pressed',v.play);$('ifc-rpm-label').textContent=f(v.rpm,1)+' rpm';$('ifc-live-motion').textContent=(v.play?'Giro':'Pausa')+' · '+f(v.rpm,1)+' rpm · visual ×'+f(v.scale,1);$('ifc-rpm').disabled=v.follow;}
function initIfcViewer(){
 const v=IFCView;v.data=JSON.parse($('ifc-data').textContent);const m=v.data.metadata;
 v.offer=m.defaultOffer||'A';v.storageKey='vawt-ifc-'+m.sha256;let restored=D.ifcView;try{if(!restored)restored=JSON.parse(sessionStorage.getItem(v.storageKey));}catch{}v.restored=restored;
 if(restored){if(m.offers?.[restored.offer])v.offer=restored.offer;for(const key of ['rpm','scale','angle'])if(Number.isFinite(restored[key]))v[key]=restored[key];v.rpm=Math.max(0,Math.min(60,v.rpm));v.scale=[.1,.2,.5,1].includes(v.scale)?v.scale:.2;v.play=!!restored.play;v.follow=!!restored.follow;}
 $('ifc-rpm').value=v.rpm;$('ifc-time-scale').value=String(v.scale).replace(/^0\./,'.');$('ifc-follow-rpm').checked=v.follow;
 setInterval(()=>{try{sessionStorage.setItem(v.storageKey,JSON.stringify(captureIfcViewState()));}catch{}},750);
 $('ifc-file-info').textContent=m.filename+' · '+m.schema+' · unidades: metros · '+m.meshes+' instancias de malla (variantes A/B) · '+m.triangles.toLocaleString('es-CL')+' triángulos · SHA-256: '+m.sha256;
 for(const l of v.data.layers){const label=document.createElement('label');label.className='ifc-layer';const input=document.createElement('input');input.type='checkbox';input.checked=restored?.hiddenLayers?!restored.hiddenLayers.includes(l.name):l.defaultVisible;input.dataset.layer=l.name;const dot=document.createElement('i');dot.className='ifc-layer-color';dot.style.background='rgb('+l.color.map(c=>Math.round(c*255)).join(',')+')';const name=document.createElement('span');name.textContent=l.name;const count=document.createElement('small');count.className='ifc-layer-count';count.textContent=l.count;label.append(input,dot,name,count);$('ifc-layers').append(label);input.onchange=()=>{if(v.layers.has(l.name))v.layers.get(l.name).visible=input.checked;applyModelVisibility();updateIfcLayerToggle();notifyIfcLayerCosts();};}
 $('ifc-all-layers').onclick=toggleIfcLayers;updateIfcLayerToggle();$('ifc-reset-layers').onclick=()=>setIfcLayers(l=>l.defaultVisible);$('ifc-rotor-only').onclick=()=>isolateIfcGroup('rotor');$('ifc-tower-only').onclick=()=>isolateIfcGroup('tower');$('ifc-foundation-only').onclick=()=>isolateIfcGroup('foundation');
 $('ifc-play').onclick=()=>{v.play=!v.play;ifcMotionLabels();v.dirty=true;};$('ifc-rpm').oninput=()=>{v.rpm=+$('ifc-rpm').value;ifcMotionLabels();};$('ifc-follow-rpm').onchange=()=>{v.follow=$('ifc-follow-rpm').checked;if(!v.follow)v.rpm=+$('ifc-rpm').value;updateIfcAnalysisContext();};$('ifc-time-scale').onchange=()=>{v.scale=+$('ifc-time-scale').value;ifcMotionLabels();};
 for(const [key,offer]of Object.entries(m.offers||{}))$('model-offer').append(element('option',{value:key},offer.label));$('model-offer').value=v.offer;$('model-offer').onchange=()=>{v.offer=$('model-offer').value;applyModelVisibility();updateModelOfferNote();if(v.selected)selectIfcPiece(v.selected);if(typeof CostView!=='undefined'&&CostView.data)renderCostDashboard();};updateModelOfferNote();
 updateIfcAnalysisContext();
 new IntersectionObserver(entries=>{v.visible=entries[0].isIntersecting;if(v.visible&&!v.ready&&!v.failed){try{createIfcScene();}catch(e){v.failed=true;$('ifc-loading').textContent='No se pudo iniciar WebGL: '+e.message;console.error(e);}}v.dirty=true;},{rootMargin:'150px'}).observe($('ifc-viewport'));
}
function createIfcScene(){
 const v=IFCView,T=THREE;v.renderer=new T.WebGLRenderer({canvas:$('ifc-canvas'),antialias:true,preserveDrawingBuffer:true,alpha:false});v.renderer.setPixelRatio(Math.min(devicePixelRatio,2));v.renderer.outputColorSpace=T.SRGBColorSpace;v.renderer.setClearColor(0xeaf0f4);v.scene=new T.Scene();v.camera=new T.PerspectiveCamera(38,1,.05,300);v.camera.up.set(0,0,1);v.target=new T.Vector3(0,0,9.1);v.distance=37;v.azimuth=-Math.PI/4;v.polar=1.13;
 v.scene.add(new T.HemisphereLight(0xffffff,0x77828a,2));const sun=new T.DirectionalLight(0xffffff,2.4);sun.position.set(-10,-16,30);v.scene.add(sun);const fill=new T.DirectionalLight(0xffffff,1);fill.position.set(16,8,15);v.scene.add(fill);
 v.rotor=new T.Group();v.rotor.rotation.z=v.angle;v.scene.add(v.rotor);v.static=new T.Group();v.scene.add(v.static);
 for(const layer of v.data.layers){const g=new T.Group();g.visible=[...$('ifc-layers').querySelectorAll('input')].find(i=>i.dataset.layer===layer.name).checked;(layer.rotating?v.rotor:v.static).add(g);v.layers.set(layer.name,g);}
 for(const p of v.data.meshes){const mesh=makeIfcProductMesh(p,T);(p.rotating?v.rotor:v.static).add(mesh);v.meshes.push(mesh);}
 const grid=new T.GridHelper(64,64,0xc4d0d8,0xd8e1e7);grid.rotation.x=Math.PI/2;grid.position.z=-1.61;v.scene.add(grid);
 applyModelVisibility();v.ray=new T.Raycaster();v.pointer=new T.Vector2();v.ready=true;$('ifc-loading').hidden=true;
 function camera(){v.camera.position.set(v.target.x+v.distance*Math.sin(v.polar)*Math.cos(v.azimuth),v.target.y+v.distance*Math.sin(v.polar)*Math.sin(v.azimuth),v.target.z+v.distance*Math.cos(v.polar));v.camera.lookAt(v.target);v.camera.updateMatrixWorld();v.dirty=true;}v.updateCamera=camera;
 function resize(){const r=$('ifc-viewport').getBoundingClientRect();v.renderer.setSize(Math.max(r.width,1),Math.max(r.height,1),false);const aspect=r.width/Math.max(r.height,1);if(v.previousAspect)v.distance*=Math.max(37,34/aspect)/Math.max(37,34/v.previousAspect);else if(!v.restored?.camera)v.distance=Math.max(37,34/aspect);v.previousAspect=aspect;v.camera.aspect=aspect;v.camera.updateProjectionMatrix();camera();}new ResizeObserver(resize).observe($('ifc-viewport'));
 v.preset=name=>{v.target.set(0,0,9.1);v.distance=Math.max(37,34/v.camera.aspect);v.azimuth=name==='side'?0:-Math.PI/2;v.polar=name==='top'?.015:Math.PI/2;if(name==='iso'){v.azimuth=-Math.PI/4;v.polar=1.13;}document.querySelectorAll('[data-ifc-camera]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.ifcCamera===name));camera();};document.querySelectorAll('[data-ifc-camera]').forEach(b=>b.onclick=()=>v.preset(b.dataset.ifcCamera));$('ifc-fit').onclick=()=>v.preset('iso');$('ifc-wireframe').onchange=()=>{v.meshes.forEach(m=>m.material.forEach(a=>a.wireframe=$('ifc-wireframe').checked));v.dirty=true;};$('ifc-snapshot').onclick=()=>{v.renderer.render(v.scene,v.camera);const a=document.createElement('a');a.download='Rotor_V80_v5_'+v.offer+'.png';a.href=v.renderer.domElement.toDataURL('image/png');a.click();};
 const canvas=$('ifc-canvas'),pointers=new Map();let start=null,lastPinch=0,moved=false;
 canvas.oncontextmenu=e=>e.preventDefault();canvas.onpointerdown=e=>{canvas.setPointerCapture(e.pointerId);pointers.set(e.pointerId,[e.clientX,e.clientY]);start=[e.clientX,e.clientY];moved=false;lastPinch=0;};
 canvas.onpointermove=e=>{if(!pointers.has(e.pointerId))return;const prev=pointers.get(e.pointerId),dx=e.clientX-prev[0],dy=e.clientY-prev[1];pointers.set(e.pointerId,[e.clientX,e.clientY]);if(start&&Math.hypot(e.clientX-start[0],e.clientY-start[1])>4)moved=true;if(pointers.size===2){const [a,b]=[...pointers.values()],distance=Math.hypot(a[0]-b[0],a[1]-b[1]);if(lastPinch)v.distance=Math.max(1,Math.min(100,v.distance*lastPinch/Math.max(distance,1)));lastPinch=distance;}else if(e.shiftKey||e.buttons===2){const right=new T.Vector3().setFromMatrixColumn(v.camera.matrixWorld,0),up=new T.Vector3().setFromMatrixColumn(v.camera.matrixWorld,1);v.target.addScaledVector(right,-dx*v.distance*.0012).addScaledVector(up,dy*v.distance*.0012);}else{v.azimuth-=dx*.007;v.polar=Math.max(.015,Math.min(Math.PI-.015,v.polar+dy*.007));}camera();};
 canvas.onpointerup=e=>{pointers.delete(e.pointerId);if(!moved&&start){const r=canvas.getBoundingClientRect();v.pointer.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1);v.ray.setFromCamera(v.pointer,v.camera);const hits=v.ray.intersectObjects(v.meshes).filter(h=>{let o=h.object;while(o){if(!o.visible)return false;o=o.parent;}return true;});if(hits[0])selectIfcPiece(hits[0].object);}start=null;};canvas.onpointercancel=e=>{pointers.delete(e.pointerId);start=null;};canvas.addEventListener('wheel',e=>{e.preventDefault();v.distance=Math.max(1,Math.min(100,v.distance*Math.exp(e.deltaY*.001)));camera();},{passive:false});canvas.onkeydown=e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-',' '].includes(e.key)){e.preventDefault();if(e.key===' ')$('ifc-play').click();if(e.key==='ArrowLeft')v.azimuth-=.12;if(e.key==='ArrowRight')v.azimuth+=.12;if(e.key==='ArrowUp')v.polar=Math.max(.015,v.polar-.1);if(e.key==='ArrowDown')v.polar=Math.min(Math.PI-.015,v.polar+.1);if(e.key==='+')v.distance*=.9;if(e.key==='-')v.distance*=1.1;camera();}};

 if(v.restored?.camera){const c=v.restored.camera;if(c.target?.length===3&&c.target.every(Number.isFinite)&&[c.distance,c.azimuth,c.polar].every(Number.isFinite)){v.target.fromArray(c.target);v.distance=Math.max(1,Math.min(100,c.distance));v.azimuth=c.azimuth;v.polar=Math.max(.015,Math.min(Math.PI-.015,c.polar));}}resize();let last=0;function tick(t){requestAnimationFrame(tick);if(t-last<33)return;const dt=last?Math.min((t-last)/1000,.1):0;last=t;if(!v.visible||document.hidden)return;if(v.play&&v.rpm>0){v.angle=(v.angle+v.rpm*2*Math.PI/60*dt*v.scale)%(2*Math.PI);v.rotor.rotation.z=v.angle;v.dirty=true;}if(v.dirty){v.scene.updateMatrixWorld(true);v.renderer.render(v.scene,v.camera);const visible=v.meshes.filter(m=>m.visible).length;$('ifc-view-stats').textContent=visible+' / '+v.data.meshes.length+' mallas · V5 '+v.offer+' · metros';v.dirty=false;}}requestAnimationFrame(tick);
}
function selectIfcPiece(mesh){const v=IFCView;if(v.selected)v.selected.material.forEach(m=>m.emissive.setHex(0));v.selected=mesh;mesh.material.forEach(m=>m.emissive.setHex(0x344519));v.play=false;ifcMotionLabels();v.dirty=true;$('ifc-canvas').title=mesh.userData.product.name;}
function focusIfcPiece(){const v=IFCView;if(!v.selected||!v.ready)return;const box=new THREE.Box3().setFromObject(v.selected);box.getCenter(v.target);v.distance=Math.max(2,box.getSize(new THREE.Vector3()).length()*1.8);v.updateCamera();}

function captureIfcViewState(){const v=IFCView;return{offer:v.offer,rpm:v.rpm,scale:v.scale,play:v.play,follow:v.follow,angle:v.angle,hiddenLayers:[...$('ifc-layers').querySelectorAll('input')].filter(i=>!i.checked).map(i=>i.dataset.layer),camera:v.ready?{target:v.target.toArray(),distance:v.distance,azimuth:v.azimuth,polar:v.polar}:v.restored?.camera};}
function decodeIfcMesh(encoded,Type){const s=atob(encoded),bytes=new Uint8Array(s.length);for(let i=0;i<s.length;i++)bytes[i]=s.charCodeAt(i);return new Type(bytes.buffer);}

function makeIfcProductMesh(p,T){const geom=new T.BufferGeometry();geom.setAttribute('position',new T.BufferAttribute(decodeIfcMesh(p.vertices,Float32Array),3));const length=p.groups.reduce((n,g)=>n+decodeIfcMesh(g.indices,Uint32Array).length,0),indices=new Uint32Array(length);let offset=0;for(const g of p.groups){const array=decodeIfcMesh(g.indices,Uint32Array);indices.set(array,offset);geom.addGroup(offset,array.length,g.material);offset+=array.length;}geom.setIndex(new T.BufferAttribute(indices,1));geom.computeVertexNormals();const materials=p.materials.map(m=>new T.MeshStandardMaterial({color:new T.Color().setRGB(...m.rgb,T.SRGBColorSpace),roughness:.72,metalness:.12,side:T.DoubleSide,transparent:m.opacity<1,opacity:m.opacity,flatShading:true}));const mesh=new T.Mesh(geom,materials);mesh.userData.product=p;return mesh;}
function modelOfferMatches(product){return !product.offer||product.offer==='AB'||product.offer===IFCView.offer;}
function applyModelVisibility(){const v=IFCView;for(const mesh of v.meshes){const p=mesh.userData.product;mesh.visible=modelOfferMatches(p)&&(v.layers.get(p.layer)?.visible??true);}if(v.selected&&!v.selected.visible){v.selected.material.forEach(m=>m.emissive.setHex(0));v.selected=null;$('ifc-canvas').removeAttribute('title');}v.dirty=true;}

function updateModelOfferNote(){const v=IFCView,offer=v.data.metadata.offers?.[v.offer];$('model-offer-note').textContent=(offer?.description||'')+' · '+(offer?.meshes||0)+' instancias de malla.';for(const label of $('ifc-layers').querySelectorAll('label')){const name=label.querySelector('input').dataset.layer;label.querySelector('small').textContent=v.data.meshes.filter(m=>m.layer===name&&modelOfferMatches(m)).length;}const summary=v.data.sourceCostSummaries?.[v.offer];$('model-source-cost-note').textContent=summary?'Costeo declarado en el HTML v5, variante '+v.offer+': US$ '+summary.total.toLocaleString('es-CL')+'; tipo de cambio del archivo: 1.000 CLP/USD. Es una estimación de ese archivo, separada de los presupuestos de Google Sheets del punto 6.':'';}

// Source weights belong to declared component groups, not individual mesh copies.
function modelGroupKey(product){return product.layer+'::'+(product.sourceId||product.id);}
function modelWeightKg(value){
 if(typeof value==='number')return Number.isFinite(value)&&value>=0?value:null;
 const match=String(value||'').match(/^\s*(?:≈|~)?\s*(\d+(?:\.\d{3})*(?:,\d+)?)\s*kg(?:\s|\(|$)/i);
 if(!match)return null;return Number(match[1].replaceAll('.','').replace(',','.'));
}
function modelGroupQuantity(value){
 if(typeof value==='number')return Number.isFinite(value)&&value>=0?value:null;
 const match=String(value??'').match(/^\s*(\d+(?:\.\d{3})*(?:,\d+)?)(?:\s+(?:elementos?|unidades?|piezas?))?\s*$/i);
 return match?Number(match[1].replaceAll('.','').replace(',','.')):null;
}
function modelUnitWeight(total,quantity){const mass=modelWeightKg(total),count=modelGroupQuantity(quantity);return mass!==null&&count!==null&&count>0?{kg:mass/count,label:(mass/count).toLocaleString('es-CL',{maximumFractionDigits:3})+' kg'}:{kg:null,label:'Sin dato'};}
function modelWeightGroups(products,offer){
 const groups=new Map();
 for(const product of products){if(product.offer&&product.offer!=='AB'&&product.offer!==offer)continue;const key=modelGroupKey(product);
  if(!groups.has(key)){const props=product.propsByOffer?.[offer]||product.props||{},unitMass=modelUnitWeight(props['Peso total'],props['Cantidad']);groups.set(key,{key,productId:product.id,name:product.sourceId||product.name,layer:product.layer,quantity:props['Cantidad']??'Sin dato',unitWeight:unitMass.label,unitKg:unitMass.kg,totalWeight:props['Peso total']??'Sin dato',totalKg:modelWeightKg(props['Peso total']),meshCount:0});}
  groups.get(key).meshCount++;
 }
 return [...groups.values()];
}
function renderModelWeights(target,groups,title,onPick,activeKey=null){
 const box=$(target);if(!box)return;box.replaceChildren();
 const section=element('section',{className:'model-weight-panel'}),heading=element('div',{className:'model-weight-heading'});
 heading.append(element('span',{},'PESOS DECLARADOS · HTML V5'),element('h4',{},title));section.append(heading);
 if(!groups.length){section.append(element('p',{className:'model-weight-note'},'No hay componentes del HTML v5 vinculados a esta selección.'));box.append(section);return;}
 const known=groups.filter(group=>group.totalKg!==null),total=known.reduce((sum,group)=>sum+group.totalKg,0),summary=element('div',{className:'model-weight-summary'});
 for(const [label,value]of [['Grupos de componentes',String(groups.length)],['Peso de grupos disponible',known.length?f(total,1)+' kg':'Sin dato']]){const item=element('div');item.append(element('span',{},label),element('strong',{},value));summary.append(item);}section.append(summary);
 const scroll=element('div',{className:'model-weight-scroll',tabIndex:0,role:'region',ariaLabel:'Pesos de los componentes del HTML v5'}),table=element('table'),thead=element('thead'),headers=element('tr');
 for(const label of ['Componente','Cantidad','Peso unitario','Peso del grupo'])headers.append(element('th',{scope:'col'},label));thead.append(headers);table.append(thead);
 const body=element('tbody');for(const group of groups){const row=element('tr'),name=element('td'),button=element('button',{type:'button',className:'model-weight-select',ariaPressed:String(group.key===activeKey)},group.name);button.dataset.modelGroup=group.key;button.onclick=()=>onPick(group);name.append(button,element('small',{},group.layer));row.append(name,element('td',{},String(group.quantity)),element('td',{},group.unitWeight),element('td',{},group.totalWeight));body.append(row);}table.append(body);scroll.append(table);section.append(scroll);
 section.append(element('p',{className:'model-weight-note'},known.length+' / '+groups.length+' grupos con peso total informado. Peso unitario = peso del grupo ÷ cantidad. Cada grupo se cuenta una sola vez. Se conserva el peso total declarado, incluidas fundaciones si aparecen en la selección; no se calcula a partir de la malla.'));
 box.append(section);
}
function showIfcWeightGroup(group){
 const v=IFCView;navigateToStep('step-5');
 const input=[...$('ifc-layers').querySelectorAll('input')].find(item=>item.dataset.layer===group.layer);if(input&&!input.checked){input.checked=true;input.onchange();}
 if(!v.ready){try{createIfcScene();}catch(error){$('ifc-loading').textContent='No se pudo iniciar la geometría. Los pesos declarados siguen disponibles en el punto 6.';return;}}
 const mesh=v.meshes.find(item=>item.userData.product.id===group.productId&&modelOfferMatches(item.userData.product));if(!mesh)return;
 selectIfcPiece(mesh);focusIfcPiece();
}

function updateIfcLayerToggle(){
 const inputs=[...$('ifc-layers').querySelectorAll('input')],all=inputs.length>0&&inputs.every(input=>input.checked),button=$('ifc-all-layers');
 button.textContent=all?'Ocultar todas':'Mostrar todas';button.setAttribute('aria-label',all?'Desmarcar todas las capas del archivo':'Seleccionar todas las capas del archivo');updateIfcIsolationState();
}
function notifyIfcLayerCosts(){if(!IFCView.layerBatch&&typeof syncCostLayersFromModel==='function')syncCostLayersFromModel();}
function setIfcLayers(predicate){
 const previous=!!IFCView.layerBatch;IFCView.layerBatch=true;
 try{for(const input of $('ifc-layers').querySelectorAll('input')){const layer=IFCView.data.layers.find(item=>item.name===input.dataset.layer);input.checked=!!predicate(layer);input.onchange();}}
 finally{IFCView.layerBatch=previous;}
 notifyIfcLayerCosts();
}
function toggleIfcLayers(){const inputs=[...$('ifc-layers').querySelectorAll('input')],show=!inputs.every(input=>input.checked);setIfcLayers(()=>show);}

function isolateIfcGroup(group){setIfcLayers(layer=>turbineLayerGroup(layer.name)===group);}
function updateIfcIsolationState(){if(typeof turbineLayerGroup!=='function')return;const inputs=[...$('ifc-layers').querySelectorAll('input')];for(const [group,id]of [['rotor','ifc-rotor-only'],['tower','ifc-tower-only'],['foundation','ifc-foundation-only']]){const button=$(id);if(!button)continue;const active=inputs.some(input=>input.checked)&&inputs.every(input=>input.checked===(turbineLayerGroup(input.dataset.layer)===group));button.setAttribute('aria-pressed',String(active));}}
