"""Selection across the model, financial context, navigation, and offline report."""
import subprocess
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NODE='/Users/jonathan.diaz/.nvm/versions/node/v24.18.0/bin/node'

class SelectedLayerCostTests(unittest.TestCase):
    def run_js(self,script):
        result=subprocess.run([NODE,'-e',script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_multiple_layers_follow_model_selection_and_survive_drilldown_and_export(self):
        self.run_js(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El{constructor(tag='div',props={},text=''){Object.assign(this,props);this.tagName=tag;this.textContent=text;this.children=[];this.dataset={};this.style={};}append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;}setAttribute(k,v){this[k]=v;}}
const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,new El());return nodes.get(id);};
const scope={console,matchMedia:()=>({matches:false}),$,element:(...args)=>new El(...args),f:(v,n)=>v.toFixed(n),document:{createElement:tag=>new El(tag)},localStorage:{setItem(){}}};
vm.createContext(scope);for(const name of ['ifc_viewer','cost_dashboard','cost_preview','cost_export'])vm.runInContext(fs.readFileSync('assets/'+name+'.js','utf8'),scope);
scope.model=JSON.parse(fs.readFileSync('data/v80_v5_mesh.json','utf8'));scope.costs=JSON.parse(fs.readFileSync('data/cost_reference_snapshot.json','utf8'));
vm.runInContext(`
IFCView.data=model;CostView.data=costs;
const chosen=['Rotor: palas','Fundación y morteros'];
const inputs=model.layers.map(layer=>({dataset:{layer:layer.name},checked:chosen.includes(layer.name),onchange(){notifyIfcLayerCosts();}}));
$('ifc-layers').querySelectorAll=()=>inputs;
let navigated=null,renders=0;renderCostDashboard=()=>renders++;navigateToStep=step=>navigated=step;
syncCostLayersFromModel();
if(navigated!==null||!costMultiActive())throw Error('automatic sync must update point 6 without moving the viewport');
const expected=costs.rows.filter(row=>row.milestone===CostView.milestone&&chosen.includes(row.sourceLayer));
if(JSON.stringify(costFilteredRows().map(r=>r.id).sort())!==JSON.stringify(expected.map(r=>r.id).sort()))throw Error('other layers leaked or selected rows missing');
if(costStats(costFilteredRows()).current!==expected.reduce((sum,row)=>sum+(row.current||0),0))throw Error('combined total');
const before=JSON.stringify(costs.rows),saved=captureCostViewState();
if(JSON.stringify(saved.selectedLayers)!==JSON.stringify(chosen))throw Error('selection not persisted');
if(costCsvData().rows.length!==expected.length)throw Error('CSV scope');
const snapshot=costAnalysisSnapshot(),report=costExportDocument(snapshot,'','<section>Snapshot</section>');
if(snapshot.tableRows.length!==expected.length||!report.includes('Capas: Rotor: palas · Fundación y morteros'))throw Error('HTML selection scope');
const products=costPreviewProducts(model,CostView,'A');
if(products.some(product=>!chosen.includes(product.layer))||!chosen.every(layer=>products.some(product=>product.layer===layer)))throw Error('geometry scope');
updateCostPreview();if($('cost-preview-title').textContent!=='2 capas seleccionadas')throw Error('combined preview title');
const groupNames=modelWeightGroups(products,'A').map(group=>group.layer);
if(groupNames.some(layer=>!chosen.includes(layer)))throw Error('weight scope');
// Drilling into one layer keeps a route back to the original selection.
showLayerCosts(chosen[0],true);if(costFilteredRows().some(row=>row.sourceLayer!==chosen[0]))throw Error('layer drilldown');
costChartBack();if(!costMultiActive()||costFilteredRows().length!==expected.length)throw Error('back lost multi selection');
costNavigation('overview');if(CostView.selectedLayers.length||costFilteredRows().length!==costScopedRows().length)throw Error('clear selection');
// With only one checkbox, the clicked layer remains the requested scope.
inputs.forEach(input=>input.checked=input.dataset.layer===chosen[0]);notifyIfcLayerCosts();
if(CostView.layer!==chosen[0]||CostView.selectedLayers[0]!==chosen[0])throw Error('automatic single layer');
// Bulk changes render once, and no checked layers must never mean every layer.
navigated=null;const previousRenders=renders;setIfcLayers(()=>false);
if(renders!==previousRenders+1||navigated!==null)throw Error('batch should render exactly once without navigation');
if(costFilteredRows().length||costPreviewProducts(model,CostView,'A').length)throw Error('empty selection leaked costs or geometry');
if(!captureCostViewState().modelSelectionActive||!costExportDocument(costAnalysisSnapshot(),'','<section></section>').includes('Sin capas seleccionadas'))throw Error('empty selection not persisted/exported');
setIfcLayers(()=>true);if(renders!==previousRenders+2)throw Error('select all batch');
if(costFilteredRows().some(row=>!model.layers.some(layer=>layer.name===row.sourceLayer)))throw Error('unselected categories leaked');
if(costValidateLayers([chosen[0],chosen[0],'unknown',42]).length!==1)throw Error('invalid or duplicate layers');
if(JSON.stringify(costs.rows)!==before)throw Error('source data changed');
`,scope);
''')

    def test_reference_budget_is_the_displayed_price_without_derived_substitutes(self):
        self.run_js(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');const scope={f:(v,n)=>v.toFixed(n)};vm.createContext(scope);vm.runInContext(fs.readFileSync('assets/cost_dashboard.js','utf8'),scope);
vm.runInContext(`
const mast={id:'A533',milestone:'Producto 80 kW',sourceLayer:'Torre',package:'Mástil',criterion:'Insumo',quantity:'8',kgPerUnit:169,hoursPerUnit:null,current:5404000,previous:4323200,referenceBudget:4000};
if(costPhysicalRate(mast).value!==4000||costMoney(costPhysicalRate(mast).value)!=='US$ 4.08')throw Error('display must use Presupuesto referencia divided by FX once');
if(costPhysicalRate({...mast,current:null,previous:null,quantity:'0',kgPerUnit:null}).value!==4000)throw Error('reference must not depend on totals, quantity or consumption');
if(costPhysicalRate({...mast,referenceBudget:null}).value!==null||costPhysicalRate({...mast,referenceBudget:undefined}).value!==null)throw Error('missing source reference must not use calculated unit cost');
if(costPhysicalRate({...mast,referenceBudget:0}).value!==0)throw Error('zero source price');
const labor={...mast,id:'A640',criterion:'HH',quantity:'6',kgPerUnit:null,hoursPerUnit:30,referenceBudget:6500};
let totals=costPhysicalRateTotals([mast,labor]);if(totals.length!==2||totals.find(group=>group.unit==='kg').amount/totals.find(group=>group.unit==='kg').quantity!==4000||totals.find(group=>group.unit==='h').amount/totals.find(group=>group.unit==='h').quantity!==6500)throw Error('reference prices mixed with published budgets');
CostView.data={rows:[mast,labor]};const csv=costCsvData(),column=csv.headers.indexOf('Costo por Kg/ HH USD');if(csv.rows[0][column]!==4000/980)throw Error('CSV reference column');
costSetDollarRate(1000);if(costMoney(costPhysicalRate(mast).value)!=='US$ 4.00')throw Error('FX conversion');
if(costPhysicalRateTotals([]).length)throw Error('empty reference totals');
`,scope);
''')

if __name__=='__main__':unittest.main()
