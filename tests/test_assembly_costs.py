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

    def test_group_kpis_only_show_in_complete_overview(self):
        self.run_js(r'''
vm.runInContext(`
IFCView.data=model;CostView.data=costs;
const full=model.layers.map(l=>l.name);
if(!costAssemblyKpisVisible())throw Error('initial overview should show groups');
CostView.modelSelectionActive=true;CostView.selectedLayers=[];
if(costAssemblyKpisVisible())throw Error('empty selection should hide groups');
CostView.selectedLayers=full.slice(1);
if(costAssemblyKpisVisible())throw Error('partial selection should hide groups');
CostView.selectedLayers=full;
if(!costAssemblyKpisVisible())throw Error('all checked layers should show groups');
CostView.layer='Fundación y morteros';
renderCostAssemblyKpis(costScopedRows());
if(!$('cost-assembly-kpis').hidden||$('cost-assembly-grid').children.length)throw Error('single foundation must hide/clear groups');
CostView.layer='all';CostView.package='one package';
if(costAssemblyKpisVisible())throw Error('package scope should hide groups');
CostView.package='all';CostView.activity='A1';
if(costAssemblyKpisVisible())throw Error('activity scope should hide groups');
CostView.activity='all';CostView.search='fundación';
if(costAssemblyKpisVisible())throw Error('search scope should hide groups');
CostView.search='';renderCostAssemblyKpis(costScopedRows());
if($('cost-assembly-kpis').hidden||$('cost-assembly-grid').children.length!==3)throw Error('restore complete overview');
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
