"""Isolation and cost shares use one physical grouping without reassigning other costs."""
import subprocess
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class AssemblyCostTests(unittest.TestCase):
    def run_js(self,body):
        bootstrap=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El{constructor(tag='div',props={},text=''){Object.assign(this,props);this.tag=tag;this.children=[];this.dataset={};this.style={};this.textContent=text;}append(...children){this.children.push(...children);}replaceChildren(...children){this.children=children;}setAttribute(k,v){this[k]=v;}}
const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,new El());return nodes.get(id);};
const scope={console,matchMedia:()=>({matches:false}),$,element:(...a)=>new El(...a),f:(n,d)=>n.toFixed(d),localStorage:{setItem(){}}};vm.createContext(scope);
for(const file of ['ifc_viewer','cost_dashboard','cost_export'])vm.runInContext(fs.readFileSync('assets/'+file+'.js','utf8'),scope);
scope.model=JSON.parse(fs.readFileSync('data/v80_v5_mesh.json','utf8'));scope.costs=JSON.parse(fs.readFileSync('data/cost_reference_snapshot.json','utf8'));
'''
        result=subprocess.run(['node','-e',bootstrap+body],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_isolation_selects_exact_groups_and_syncs_once(self):
        self.run_js(r'''
vm.runInContext(`
IFCView.data=model;CostView.data=costs;let renders=0;renderCostDashboard=()=>renders++;
const inputs=model.layers.map(layer=>({dataset:{layer:layer.name},checked:true,onchange(){notifyIfcLayerCosts();}}));$('ifc-layers').querySelectorAll=()=>inputs;
const expectedTower=['Torre: montantes y riostras','Pernos y fijaciones de torre','Placas y conexiones de torre','Cabezal y soportes nuevos'];
for(const group of ['rotor','tower','foundation']){const before=renders;isolateIfcGroup(group);if(renders!==before+1)throw Error('isolation must sync once');const selected=inputs.filter(i=>i.checked).map(i=>i.dataset.layer);if(selected.some(name=>turbineLayerGroup(name)!==group))throw Error('mixed physical groups');if(group==='tower'&&JSON.stringify(selected.sort())!==JSON.stringify(expectedTower.sort()))throw Error('tower membership');if(group==='foundation'&&JSON.stringify(selected)!==JSON.stringify(['Fundación y morteros']))throw Error('foundation must stand alone');if(group==='rotor'&&!selected.includes('Tren de potencia'))throw Error('powertrain lost');if(costChartRows().some(r=>turbineLayerGroup(costLayer(r))!==group))throw Error('cost selection diverges from geometry');}
`,scope);
''')

    def test_values_percentages_missing_and_other_costs(self):
        self.run_js(r'''
vm.runInContext(`
const row=(id,layer,current,previous)=>({id,sourceLayer:layer,current,previous});
const data=[row('1','Rotor: palas',100,80),row('2','Tren de potencia',50,40),row('3','Cabezal y soportes nuevos',20,10),row('4','Pernos y fijaciones de torre',30,20),row('5','Placas y conexiones de torre',10,10),row('6','Torre: montantes y riostras',40,30),row('7','Fundación y morteros',50,40),row('8','Transporte',100,70),row('9','Rotor: brazos',null,null)];
const s=costAssemblySummary(data,'current');if(s.total.current!==400)throw Error('denominator');
const rotor=s.groups.find(g=>g.key==='rotor'),tower=s.groups.find(g=>g.key==='tower'),foundation=s.groups.find(g=>g.key==='foundation');
if(rotor.amount!==150||rotor.percent!==37.5||tower.amount!==100||tower.percent!==25||foundation.amount!==50||foundation.percent!==12.5)throw Error('group values/shares');
if(s.otherCount!==1||s.otherStats.current!==100)throw Error('unmapped cost hidden or assigned arbitrarily');
if(s.groups.reduce((n,g)=>n+g.amount,0)+s.otherStats.current!==s.total.current)throw Error('double counting');
const prior=costAssemblySummary(data,'previous');if(prior.groups.find(g=>g.key==='rotor').amount!==120)throw Error('basis selector');
const missing=costAssemblySummary([row('x','Fundación y morteros',null,0)]);if(missing.groups.find(g=>g.key==='foundation').amount!==null)throw Error('missing became zero');
const empty=costAssemblySummary([]);if(empty.groups.length!==3||empty.groups.some(g=>g.percent!==null))throw Error('empty percentages');
renderCostAssemblyKpis(data);if($('cost-assembly-grid').children.length!==3)throw Error('three KPI');
if(turbineLayerGroup('Fundación')!==null||turbineLayerGroup('Sistema Freno')!==null)throw Error('source categories silently reassigned');
`,scope);
''')

    def test_group_kpis_show_for_two_or_more_selected_assemblies(self):
        self.run_js(r'''
vm.runInContext(`
IFCView.data=model;CostView.data=costs;
const full=model.layers.map(l=>l.name);
if(!costAssemblyKpisVisible())throw Error('initial overview should show groups');
CostView.modelSelectionActive=true;CostView.selectedLayers=[];
if(costAssemblyKpisVisible())throw Error('empty selection should hide groups');
CostView.selectedLayers=full.slice(1);
if(!costAssemblyKpisVisible())throw Error('multiple assemblies must retain their KPI');
CostView.selectedLayers=full.filter(name=>['rotor','tower'].includes(turbineLayerGroup(name)));renderCostAssemblyKpis(costChartRows());
const cards=$('cost-assembly-grid').children;
if($('cost-assembly-kpis').hidden||cards.length!==2||cards.map(c=>c.dataset.costAssembly).join()!=='rotor,tower')throw Error('selected pair cards');
if($('cost-assembly-grid').dataset.columns!=='2')throw Error('pair layout');
const summary=costAssemblySummary(costChartRows());if(Math.abs(summary.groups.filter(g=>g.count).reduce((sum,g)=>sum+g.percent,0)-100)>1e-7)throw Error('selected denominator');
CostView.selectedLayers=full.filter(name=>turbineLayerGroup(name)==='rotor');
if(costAssemblyKpisVisible())throw Error('one assembly should hide group comparisons');
CostView.selectedLayers=full;
if(!costAssemblyKpisVisible())throw Error('all checked layers should show groups');
CostView.layer='Fundación y morteros';
renderCostAssemblyKpis(costScopedRows());
if(!$('cost-assembly-kpis').hidden||$('cost-assembly-grid').children.length)throw Error('single foundation must hide/clear groups');
CostView.layer='all';CostView.package='one package';
if(!costAssemblyKpisVisible())throw Error('package drilldown must retain multi-assembly context');
CostView.package='all';CostView.activity='A1';
if(costAssemblyKpisVisible())throw Error('activity scope should hide groups');
CostView.activity='all';CostView.search='fundación';
if(!costAssemblyKpisVisible())throw Error('multi-assembly selection must retain comparisons during search');
CostView.search='';renderCostAssemblyKpis(costScopedRows());
if($('cost-assembly-kpis').hidden||$('cost-assembly-grid').children.length!==3)throw Error('restore complete overview');
`,scope);
''')

    def test_title_changes_only_for_complete_isolated_model_groups(self):
        self.run_js(r'''
vm.runInContext(`
IFCView.data=model;
const general='Costos de la turbina y sus capas',names=model.layers.map(l=>l.name);
const state={modelSelectionActive:true,selectedLayers:names,layer:'all'};
if(costSectionTitle(state)!==general)throw Error('all layers should keep title');
for(const [group,title]of [['rotor','Costos del rotor'],['tower','Costos de la torre'],['foundation','Costos de fundación y morteros']]){
 state.selectedLayers=names.filter(name=>turbineLayerGroup(name)===group);state.layer=state.selectedLayers.length===1?state.selectedLayers[0]:'all';
 if(costSectionTitle(state)!==title)throw Error('isolated group title: '+group);
 state.modelSelectionActive=false;
 if(costSectionTitle(state)!==general)throw Error('ordinary filter should not rename heading');
 state.modelSelectionActive=true;
}
state.layer='all';state.selectedLayers=['Rotor: palas'];
if(costSectionTitle(state)!==general)throw Error('partial group should not rename heading');
state.selectedLayers=[];
if(costSectionTitle(state)!==general)throw Error('empty selection title');
`,scope);
''')

    def test_power_cost_uses_wholesale_80_kw_and_exchange_rate(self):
        self.run_js(r'''
vm.runInContext(`
const rows=[{current:100000000,previous:78400000},{current:100,previous:null}];
const render=()=>{renderCostKpis(rows,costStats(rows));return $('cost-metrics').children;};
CostView.fxRate=980;let cards=render();
if(cards.length!==5||!cards[3].className.includes('capacity')||!cards[2].className.includes('delta'))throw Error('power KPI must follow comparison');
let texts=cards[3].children.map(c=>c.textContent);
if(!texts.includes('US$ 1000.00 / kW')||!texts.includes('US$ 1000000.00 / MW'))throw Error('wholesale / 80 kW or / 0.08 MW');
if(!texts.some(t=>t.includes('subtotal parcial')))throw Error('missing costs must remain visible');
CostView.fxRate=1000;cards=render();
if(!cards[3].children.some(c=>c.textContent==='US$ 980.00 / kW'))throw Error('rate not applied');
rows[0].previous=null;cards=render();
if(!cards[3].children.some(c=>c.textContent==='Sin dato / kW'))throw Error('missing is not zero');
rows[0].previous=0;cards=render();
if(!cards[3].children.some(c=>c.textContent==='US$ 0.00 / kW'))throw Error('published zero should be preserved');
`,scope);
''')

    def test_declared_mass_splits_groups_without_duplicate_mesh_weight(self):
        self.run_js(r'''
vm.runInContext(`
for(const variant of ['A','B']){
 const groups=modelWeightGroups(model.meshes,variant),mass=modelAssemblyMasses(groups);
 if(!mass.complete)throw Error('all three assemblies must be present');
 const total=groups.reduce((sum,g)=>sum+(g.totalKg??0),0);
 if(Math.abs(mass.total-total)>1e-7)throw Error('assembly mass does not reconcile with declared groups');
 if(mass.assemblies.find(g=>g.key==='foundation').kg!==41785)throw Error('foundation mass');
 const rotor=groups.filter(g=>turbineLayerGroup(g.layer)==='rotor');
 if(modelAssemblyMasses(rotor).complete)throw Error('isolated rotor should use the single-mass summary');
}
const missing=modelAssemblyMasses([{layer:'Rotor: palas',totalKg:null},{layer:'Torre: montantes y riostras',totalKg:0},{layer:'Fundación y morteros',totalKg:10}]);
if(missing.assemblies[0].kg!==null||missing.assemblies[1].kg!==0||missing.total!==10)throw Error('missing/zero mass changed');
`,scope);
''')

    def test_dock_can_combine_toggle_and_clear_groups(self):
        self.run_js(r'''
vm.runInContext(`
IFCView.data=model;CostView.data=costs;
if(costDockGroups()!==null)throw Error('overview must remain distinct from empty');
const apply=group=>{const selected=costToggleDockGroup(costDockGroups(),group),layers=model.layers.map(l=>l.name).filter(name=>selected.includes(turbineLayerGroup(name)));Object.assign(CostView,{selectedLayers:layers,modelSelectionActive:true,layer:layers.length===1?layers[0]:'all'});return selected;};
apply('rotor');apply('tower');
if(costDockGroups().join()!=='rotor,tower'||costSectionTitle()!=='Costos de rotor y torre')throw Error('combined state/title');
if(costChartRows().some(r=>!['rotor','tower'].includes(turbineLayerGroup(costLayer(r)))))throw Error('unselected costs leaked');
apply('rotor');if(costDockGroups().join()!=='tower')throw Error('toggle must preserve other active groups');
apply('foundation');if(costDockGroups().join()!=='tower,foundation')throw Error('second combination');
apply('tower');apply('foundation');
if(costDockGroups().length||costChartRows().length||!costEmptyModelSelection())throw Error('empty must not mean everything');
const saved=captureCostViewState();if(!saved.modelSelectionActive||saved.selectedLayers.length)throw Error('empty persistence');
`,scope);
''')

    def test_snapshot_includes_same_group_totals(self):
        self.run_js(r'''
vm.runInContext(`
IFCView.data=model;CostView.data=costs;const CostPreview={sourceKey:null};
const original=JSON.stringify(costs.rows),snapshot=costAnalysisSnapshot();
const total=snapshot.assembly.groups.reduce((n,g)=>n+(g.amount||0),0)+snapshot.assembly.otherStats[snapshot.assembly.base];
if(total!==snapshot.assembly.total[snapshot.assembly.base])throw Error('export groups reconciliation');
if(JSON.stringify(costs.rows)!==original)throw Error('source rows changed');
`,scope);
''')
