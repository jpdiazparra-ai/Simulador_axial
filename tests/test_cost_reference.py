import csv
import io
import json
import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch
from cost_reference import parse_quantity, parse_money, parse_cost_csv, load_cost_reference, REQUIRED

ROOT=Path(__file__).resolve().parents[1]

class CostReferenceTests(unittest.TestCase):
    def test_published_snapshot_reconciles(self):
        data=parse_cost_csv((ROOT/'data/cost_reference_source.csv').read_bytes())
        self.assertEqual((data['metadata']['sourceRecords'],len(data['rows']),data['metadata']['excluded']),(641,222,419))
        rows=[r for r in data['rows'] if r['milestone']=='Producto 80 kW']
        self.assertEqual(len(rows),103)
        self.assertEqual(sum(r['current'] or 0 for r in rows),112463579)
        self.assertEqual(sum(r['previous'] or 0 for r in rows),75131385)
        self.assertEqual(sum(r['current'] is None for r in rows),16)
        self.assertEqual(sum(r['previous'] is None for r in rows),16)
        self.assertEqual(sum(r['current']-r['previous'] for r in rows if r['current'] is not None and r['previous'] is not None),37332194)
        linked=[r for r in rows if r['sourceLayer']=='Torre: montantes y riostras']
        self.assertEqual(len(linked),6)
        self.assertEqual(sum(r['current'] for r in linked),7874165)
        self.assertTrue(all(r['applies']=='Aplica' for r in data['rows']))
        self.assertEqual(len({r['id'] for r in data['rows']}),222)

    def test_quantity_preserves_missing_zero_and_decimal_comma(self):
        self.assertEqual(parse_quantity('72'),72)
        self.assertEqual(parse_quantity('1.250,5'),1250.5)
        self.assertEqual(parse_quantity('0'),0)
        self.assertIsNone(parse_quantity('—'))
        self.assertIsNone(parse_quantity(''))
        self.assertIsNone(parse_quantity('por definir'))
        data=parse_cost_csv((ROOT/'data/cost_reference_source.csv').read_bytes())
        row=next(r for r in data['rows'] if r['id']=='A531')
        self.assertEqual(row['quantityValue'],72)
        self.assertEqual(row['current']/row['quantityValue'],6500)
        self.assertEqual(row['previous']/row['quantityValue'],3250)

    def test_html_cost_unit_and_percentage_helpers(self):
        script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('assets/cost_dashboard.js','utf8');
const helpers=source.slice(source.indexOf('const COST_UNITS='),source.indexOf('function costNavigation('));
const scope={};vm.createContext(scope);vm.runInContext(helpers,scope);
const row={criterion:'HH',quantity:'72',current:468000,previous:234000};
assert.equal(scope.costKind(row),'hh');assert.equal(scope.costQuantity(row),72);
assert.equal(scope.costUnit(row,'current'),6500);assert.equal(scope.costUnit(row,'previous'),3250);
assert(Math.abs(scope.costPercent(row.current,1134000)-41.269841269841265)<1e-10);
assert.equal(scope.costQuantity({quantity:'1.250,5'}),1250.5);
assert.equal(scope.costUnit({quantity:'0',current:1200},'current'),null);
assert.equal(scope.costUnit({quantity:'—',current:1200},'current'),null);
assert.equal(scope.costUnit({quantity:'3',current:null},'current'),null);
assert.equal(scope.costUnit({quantity:'3',current:0},'current'),0);
assert.equal(scope.costPercent(null,100),null);assert.equal(scope.costPercent(10,0),null);
"""
        result=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_missing_amount_is_not_zero(self):
        for value in ('','—','–','-','N/A'):
            self.assertIsNone(parse_money(value))
        self.assertEqual(parse_money('0'),0)
        self.assertEqual(parse_money('1.234.567'),1234567)
        self.assertEqual(parse_money('-120.000'),-120000)
        for value in ('1.23','pendiente','12,5'):
            with self.assertRaises(ValueError):parse_money(value)

    def test_filter_is_exact_and_quantity_does_not_multiply_budget(self):
        output=io.StringIO();writer=csv.writer(output)
        headers=[*REQUIRED,'Cantidad'];writer.writerow(headers)
        def row(ident,applies):
            values={'ID':ident,'Hito objetivo':'Producto 80 kW','Presupuesto vigente':'1.000','Comercial anterior':'—','Costo para producto':applies,'Cantidad':'20'}
            return [values.get(h,'') for h in headers]
        writer.writerow(row('A1',' Aplica '));writer.writerow(row('A2','No aplica'));writer.writerow(row('A3','aplicable'))
        data=parse_cost_csv(output.getvalue())
        self.assertEqual(len(data['rows']),1)
        self.assertEqual(data['rows'][0]['current'],1000)
        self.assertIsNone(data['rows'][0]['previous'])
        self.assertEqual(data['rows'][0]['sourceRow'],2)
        with self.assertRaises(ValueError):parse_cost_csv(output.getvalue()+','.join(row('A1','Aplica'))+'\n')

    def test_summary_sheet_is_rejected(self):
        with self.assertRaises(ValueError):parse_cost_csv('Resumen,Presupuesto\nTotal,100\n')

    def test_network_failure_uses_snapshot_with_explicit_status(self):
        load_cost_reference.clear()
        with patch('cost_reference.urllib.request.urlopen',side_effect=OSError('offline')):
            data=load_cost_reference()
        self.assertEqual(data['metadata']['status'],'snapshot')
        self.assertEqual(len(data['rows']),222)
        load_cost_reference.clear()

class CostDollarDisplayTests(unittest.TestCase):
    def test_usd_conversion_export_and_saved_rate_preserve_clp_source(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const scope={f:(value,digits)=>value.toLocaleString('es-CL',{minimumFractionDigits:digits,maximumFractionDigits:digits})};
vm.createContext(scope);vm.runInContext(fs.readFileSync('assets/cost_dashboard.js','utf8'),scope);
vm.runInContext(`
const rows=[{id:'A1',sourceRow:2,milestone:'Producto 80 kW',system:'Rotor',package:'Aspas',activity:'Fabricación',sourceLayer:'Aspas',criterion:'HH',quantity:'10',current:98000,previous:49000,applies:'Aplica',approved:'Sí'},
{id:'A2',sourceRow:3,milestone:'Producto 80 kW',system:'Rotor',package:'Aspas',activity:'Control',sourceLayer:'Aspas',criterion:'Insumo',quantity:'1',current:0,previous:null,applies:'Aplica',approved:'Sí'}];
CostView.data={rows};const original=JSON.stringify(rows);
if(!costSetDollarRate(980))throw Error('Invalid default');
if(costUsd(98000)!==100||costUsd(0)!==0||costUsd(null)!==null||costUsd(-980)!==-1)throw Error('Conversion');
if(costMoney(98000)!=='US$ 100,00'||costUnitMoney(9800)!=='US$ 10,00'||costMoney(null)!=='Sin dato')throw Error('Formatting');
const csv=costCsvData(),column=name=>csv.headers.indexOf(name);
if(csv.rows[0][column('Total al detalle USD')]!==100||csv.rows[0][column('Total por mayor USD')]!==50)throw Error('CSV totals');
if(csv.rows[0][column('Costo al detalle USD')]!==10||csv.rows[0][column('Diferencia comparable USD')]!==50)throw Error('CSV derived');
if(csv.rows[0][column('Tipo de cambio CLP/USD')]!==980)throw Error('CSV rate');
if(csv.rows[1][column('Total al detalle USD')]!==0||csv.rows[1][column('Total por mayor USD')]!==null)throw Error('CSV missing and zero');
if(csv.rows[0][column('Variación frente costo por mayor %')]!==100)throw Error('Ratios');
if(!costSetDollarRate(1960)||costUsd(98000)!==50||captureCostViewState().fxRate!==1960)throw Error('Rate update/persistence');
for(const invalid of [0,-1,NaN,Infinity,'',10001])if(costSetDollarRate(invalid)||CostView.fxRate!==1960)throw Error('Invalid rate accepted');
if(JSON.stringify(rows)!==original)throw Error('Source changed');
CostView.layer='Aspas';CostView.package='Aspas';CostView.activity='A1';
if(costCsvData().rows.length!==1)throw Error('Selection lost');
`,scope);
'''
        result=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_rate_control_remains_without_panorama_panel_and_headers_use_usd(self):
        from html.parser import HTMLParser
        html=(ROOT/'assets/results_visualizer.html').read_text()
        panel=html[html.index('<div class="cost-utility-bar">'):html.index('<div class="cost-metrics"')]
        self.assertNotIn('<div class="cost-trace-panel">',html)
        self.assertIn('id="cost-dollar-rate"',panel)
        self.assertIn('CLP por 1 USD',panel)
        table=html[html.index('<table id="cost-table"'):html.index('</thead>',html.index('<table id="cost-table"'))]
        self.assertNotIn('CLP',table)
        self.assertEqual(table.count('USD'),6)
        HTMLParser().feed(html)

class BoardCostChartTests(unittest.TestCase):
    def test_ranking_scales_expand_and_drilldown_preserve_source(self):
        script=r'''
const fs=require('fs'),vm=require('vm');
class Node{constructor(tag,props={},text=''){this.tag=tag;Object.assign(this,props);this.textContent=text;this.children=[];this.style={};this.dataset={};}append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=[...nodes];}setAttribute(name,value){this[name]=value;}}
const nodes={},node=id=>nodes[id]||(nodes[id]=new Node('div'));
const scope={f:(value,digits)=>value.toLocaleString('es-CL',{minimumFractionDigits:digits,maximumFractionDigits:digits}),$:node,element:(...args)=>new Node(...args)};
vm.createContext(scope);vm.runInContext(fs.readFileSync('assets/cost_dashboard.js','utf8'),scope);
vm.runInContext(`
const rows=Array.from({length:20},(_,i)=>({id:'A'+i,milestone:'Producto 80 kW',sourceLayer:'Capa '+i,package:'Paquete '+i,activity:'Actividad '+i,current:(20-i)*980,previous:(i+1)*980}));
rows[19].current=-980;rows[19].previous=-1960;CostView.data={rows};const original=JSON.stringify(rows);
const all=(root,cls)=>[...(root.className===cls?[root]:[]),...root.children.flatMap(n=>typeof n==='object'?all(n,cls):[])];
const texts=root=>[root.textContent,...root.children.flatMap(n=>typeof n==='object'?texts(n):[n])].join(' ');
let clicked=null,changes=0;showLayerCosts=layer=>clicked=layer;renderCostDashboard=()=>changes++;
const board=costBoardData(rows);if(board.groups.length!==20||board.groups[0].key!=='Capa 0'||board.minimum!==-1960)throw Error('Groups/order/negative axis');
renderCostLayers(rows);let chart=$('cost-layer-chart');
if(all(chart,'cost-board-row').length!==8)throw Error('Executive focus');
if(!texts(chart).includes('Costo al detalle')||!texts(chart).includes('Costo por mayor')||!texts(chart).includes('US$ 20,00'))throw Error('Names or USD values');
all(chart,'cost-board-row')[0].onclick();if(clicked!=='Capa 0')throw Error('Drilldown');
const footer=all(chart,'cost-board-bottom')[0];footer.children.find(n=>n.tag==='button').onclick();
if(all(chart,'cost-board-row').length!==20)throw Error('Expand all');
const fills=all(chart,'cost-board-fill');if(fills.some(n=>parseFloat(n.style.left)<0||parseFloat(n.style.width)<0||parseFloat(n.style.left)+parseFloat(n.style.width)>100.0001))throw Error('Bar geometry');
const top=all(chart,'cost-board-top')[0];top.children[1].children[1].onclick();
if(CostView.chartBase!=='previous'||changes!==1||costBoardData(rows).groups[0].key!=='Capa 18')throw Error('Commercial ordering');
costSetDollarRate(1960);renderCostLayers(rows);if(!texts(chart).includes('US$ 9,50'))throw Error('FX update of the largest visible wholesale bar');
CostView.layer='Capa 0';CostView.package='Paquete 0';if(costBoardData(rows.slice(0,1)).by!=='package')throw Error('Package selection must not drill into activities');
CostView.package='all';if(costBoardData(rows.slice(0,1)).by!=='package')throw Error('Package grouping');
if(JSON.stringify(rows)!==original)throw Error('Source mutation');
renderCostLayers([]);if(!texts(chart).includes('No hay partidas'))throw Error('Empty state');
`,scope);
'''
        result=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

class CostLayoutStabilityTests(unittest.TestCase):
    def test_preview_updates_only_when_css_dimensions_change(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const scope={};vm.createContext(scope);vm.runInContext(fs.readFileSync('assets/cost_preview.js','utf8'),scope);
const preview={};let updates=0;
for(let i=0;i<100;i++){if(scope.costPreviewSize(preview,{width:430.1,height:520.1}))updates++;}
assert.equal(updates,1);assert.equal(preview.width,430);assert.equal(preview.height,520);
assert.equal(scope.costPreviewSize(preview,{width:430.2,height:520.2}),null);
assert.equal(scope.costPreviewSize(preview,{width:0,height:520}),null);
assert.equal(scope.costPreviewSize(preview,{width:Infinity,height:520}),null);
assert.equal(scope.costPreviewSize(preview,{width:300,height:380}).height,380);
assert.equal(scope.costPreviewSize(preview,{width:300,height:380}),null);
'''
        result=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_graph_has_no_resize_redraw_loop_and_canvas_cannot_grow_layout(self):
        js=(ROOT/'assets/cost_dashboard.js').read_text()
        html=(ROOT/'assets/results_visualizer.html').read_text()
        self.assertNotIn('new ResizeObserver',js)
        self.assertIn('#cost-preview-canvas{position:absolute;inset:0;',html)
        self.assertIn('.cost-preview-card #cost-preview-viewport{flex:1 1 0;min-height:240px;height:auto}',html)
        self.assertIn('align-self:stretch',html[html.index('/* Match the chart row'):html.index('#step-6{')])
        self.assertNotIn('position:sticky',html[html.index('/* Match the chart row'):html.index('#step-6{')])
        self.assertNotIn('justify-content:center',html[html.index('/* Match the chart row'):html.index('#step-6{')])

class PackageTableFilterTests(unittest.TestCase):
    def test_package_filters_table_and_export_without_changing_layer_chart(self):
        script=r'''
const fs=require('fs'),vm=require('vm');
class Node{constructor(tag,props={},text=''){this.tag=tag;Object.assign(this,props);this.textContent=text;this.children=[];this.style={};this.dataset={};}append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=[...nodes];}setAttribute(name,value){this[name]=value;}}
const nodes={},scope={location:{protocol:'http:'},IFCView:{offer:'A'},f:(v,n)=>v.toFixed(n),$:id=>nodes[id]||(nodes[id]=new Node('div')),element:(...args)=>new Node(...args)};
vm.createContext(scope);vm.runInContext(fs.readFileSync('assets/cost_dashboard.js','utf8'),scope);
vm.runInContext(`
const rows=[['A1','Aspas','Fabricación Aspa',980],['A2','Aspas','Moldes',1960],['A3','Aspas','Fabricación Aspa',2940],['A4','Torre','Montaje',10000]].map(([id,sourceLayer,package,current])=>({id,sourceLayer,package,current,previous:current/2,milestone:'Producto 80 kW',activity:'Actividad '+id,system:sourceLayer}));
CostView.data={rows,metadata:{fetchedAt:'2026-11-25T12:00:00Z',status:'snapshot',sourceRecords:4,included:4,excluded:0,sheet:'Costos',sha256:'test'}};
CostView.layer='Aspas';let chart=[],table=[],kpis=[];
renderCostTrace=()=>{};renderCostKpis=values=>kpis=values;renderCostLayers=values=>chart=values;renderCostTable=values=>table=values;updateCostPreview=()=>{};updateIfcCostSelection=()=>{};
renderCostDashboard();if(chart.length!==3||table.length!==3)throw Error('Initial layer');
CostView.package='Fabricación Aspa';renderCostDashboard();
if(chart.length!==3||kpis.length!==3||table.length!==2||table.some(row=>row.package!=='Fabricación Aspa'))throw Error('Package must filter table only');
if(costBoardData(chart).by!=='package'||costBoardData(chart).groups.length!==2)throw Error('Unexpected activity drilldown');
if(costCsvData().rows.length!==2||!$('cost-table-count').textContent.includes('Fabricación Aspa'))throw Error('Export/count filter');
CostView.package='all';renderCostDashboard();if(table.length!==3)throw Error('Clear package');
CostView.package='Fabricación Aspa';costChartBack();if(CostView.layer!=='all'||CostView.package!=='all')throw Error('Layer back');
`,scope);
'''
        result=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

class ReferenceBudgetColumnTests(unittest.TestCase):
    def test_reference_budget_is_read_directly_and_preserves_missing_and_zero(self):
        out=io.StringIO();writer=csv.writer(out);headers=[*REQUIRED,'Cantidad','Criterio','Presupuesto\nreferencia'];writer.writerow(headers)
        for ident,reference in [('A1','4.000'),('A2','0'),('A3',''),('A4','—')]:
            values={'ID':ident,'Hito objetivo':'Producto 80 kW','Costo para producto':'Aplica','Presupuesto vigente':'5.404.000','Comercial anterior':'4.323.200','Cantidad':'8','Criterio':'Insumo','Presupuesto\nreferencia':reference}
            writer.writerow([values.get(name,'') for name in headers])
        rows=parse_cost_csv(out.getvalue())['rows']
        self.assertEqual([row['referenceBudget'] for row in rows],[4000,0,None,None])
        self.assertTrue(all(row['current']==5404000 and row['previous']==4323200 for row in rows))
        archive=parse_cost_csv((ROOT/'data/cost_reference_source.csv').read_bytes())
        snapshot=json.loads((ROOT/'data/cost_reference_snapshot.json').read_text())
        self.assertEqual({row['id']:row['referenceBudget'] for row in archive['rows']},{row['id']:row['referenceBudget'] for row in snapshot['rows']})

class CostColumnUnitsTests(unittest.TestCase):
    def test_explicit_source_unit_is_preserved(self):
        output=io.StringIO();writer=csv.writer(output)
        headers=[*REQUIRED,'Cantidad','Criterio','Unidad de medida','Hrs por unidad','Kg por unidad'];writer.writerow(headers)
        values={'ID':'A1','Hito objetivo':'Producto 80 kW','Presupuesto vigente':'1.000','Comercial anterior':'800','Costo para producto':'Aplica','Cantidad':'4','Criterio':'Insumo','Unidad de medida':'kg','Hrs por unidad':'30','Kg por unidad':'150'}
        writer.writerow([values.get(field,'') for field in headers])
        parsed=parse_cost_csv(output.getvalue())['rows'][0]
        self.assertEqual(parsed['unit'],'kg')
        self.assertEqual(parsed['hoursPerUnit'],30)
        self.assertEqual(parsed['kgPerUnit'],150)
        self.assertTrue(parsed['hasPerUnitColumns'])

    def test_source_consumption_columns_prices_and_totals(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,props={},text=''){this.tag=tag;Object.assign(this,props);this.textContent=text;this.children=[];this.style={};this.dataset={};}append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=[...nodes];}setAttribute(name,value){this[name]=value;}createTFoot(){this.tFoot=new Node('tfoot');this.tFoot.owner=this;return this.tFoot;}remove(){if(this.owner)this.owner.tFoot=null;}}
const nodes={},scope={assert,Node,IFCView:{data:{layers:[{name:'Aspas'}]}},f:(v,n)=>v.toLocaleString('es-CL',{minimumFractionDigits:n,maximumFractionDigits:n}),$:id=>nodes[id]||(nodes[id]=new Node('div')),element:(...args)=>new Node(...args)};
vm.createContext(scope);vm.runInContext(fs.readFileSync('assets/cost_dashboard.js','utf8'),scope);
vm.runInContext(`
const rows=[{id:'A1',criterion:'HH',quantity:'2',hoursPerUnit:10,kgPerUnit:null,referenceBudget:49,current:980,previous:490},{id:'A2',criterion:'hh',quantity:'3',hoursPerUnit:20,kgPerUnit:null,referenceBudget:49,current:2940,previous:null},{id:'A3',criterion:'Insumo',unit:'kg',quantity:'4',hoursPerUnit:null,kgPerUnit:150,referenceBudget:7,current:3920,previous:1960},{id:'A4',criterion:'Insumo',quantity:'5',current:4900,previous:1960},{id:'A5',criterion:'HH',quantity:'0',current:100,previous:null}].map(row=>({...row,sourceLayer:'Aspas',sourceRow:2,system:'Rotor',milestone:'Producto 80 kW',package:'Fabricación',activity:'Fabricación',applies:'Aplica'}));
CostView.data={rows};const original=JSON.stringify(rows);
assert.equal(costQuantityUnit(rows[0]),'h');assert.equal(costQuantityUnit(rows[2]),'kg');assert.equal(costQuantityUnit(rows[3]),'');assert.equal(costQuantityUnit({criterion:'kg / unidad'}),'kg');
const totals=costColumnTotals(rows),hours=totals.groups.find(group=>group.unit==='h');
assert.equal(totals.groups.length,3);assert.equal(totals.missingUnit,0);assert.equal(hours.quantity,80);assert.equal(hours.currentAmount/hours.currentQuantity,49);assert.equal(hours.previousAmount/hours.previousQuantity,24.5);
assert.equal(totals.groups.find(group=>group.unit==='kg').quantity,600);
const table=$('cost-table');table.tBodies=[new Node('tbody')];let changed=0;renderCostDashboard=()=>changed++;
renderCostTable(rows);
assert.equal(table.tBodies[0].children.length,5);for(const row of table.tBodies[0].children)assert.equal(row.children.length,14);
const footer=table.tFoot.children[0];assert.equal(footer.children.reduce((n,cell)=>n+(cell.colSpan||1),0),14);
const texts=root=>[root.textContent,...root.children.flatMap(child=>typeof child==='object'?texts(child):[child])].join(' ');
assert(texts(footer).includes('80,00 h totales'));assert(texts(footer).includes('600,00 kg totales'));assert(texts(footer).includes('Promedio ponderado'));assert(texts(footer).includes('US$ 0,05 / h'));
assert.equal(table.tBodies[0].children[0].children[4].textContent,'10');assert.equal(table.tBodies[0].children[2].children[5].textContent,'150');
assert.equal(table.tBodies[0].children[0].children[6].textContent,'US$ 0,05 / h');
assert.equal(table.tBodies[0].children[0].children[7].textContent,'US$ 0,50');
assert.equal(table.tBodies[0].children[0].children[8].textContent,'US$ 0,25');
assert.equal(costCsvData().rows[0][costCsvData().headers.indexOf('Costo por Kg/ HH USD')],0.05);
const csv=costCsvData();assert(!csv.headers.some(name=>name.includes('Participación')));assert.equal(csv.rows[2][csv.headers.indexOf('Unidad costo Kg/ HH')],'kg');assert.equal(csv.rows[2][csv.headers.indexOf('Kg por unidad')],150);assert.equal(csv.rows[0][csv.headers.indexOf('Hrs por unidad')],10);assert(csv.headers.includes('Costo por mayor USD'));assert(csv.headers.includes('Total al detalle USD'));assert(csv.headers.includes('Total por mayor USD'));
assert.equal(JSON.stringify(rows),original);
`,scope);
'''
        result=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

class CarenadoConsumptionTests(unittest.TestCase):
    def test_source_factors_define_prices_without_changing_published_totals(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');const scope={assert};vm.createContext(scope);vm.runInContext(fs.readFileSync('assets/cost_dashboard.js','utf8'),scope);
vm.runInContext(`
const material={id:'A639',criterion:'Kg',quantityValue:6,kgPerUnit:150,hoursPerUnit:null,hasPerUnitColumns:true,referenceBudget:18000,current:13500000,previous:10800000};
const labor={id:'A640',criterion:'HH',quantityValue:6,hoursPerUnit:30,kgPerUnit:null,hasPerUnitColumns:true,referenceBudget:6500,current:1170000,previous:936000};
assert.equal(costPerUnit(material,'kgPerUnit'),150);assert.equal(costPerUnit(labor,'hoursPerUnit'),30);
assert.equal(costUnitBasis(material).quantity,900);assert.equal(costUnitBasis(labor).quantity,180);
assert.equal(costUnit(material,'current'),15000);assert.equal(costUnit(material,'previous'),12000);
assert.equal(costUnit(labor,'current'),6500);assert.equal(costUnit(labor,'previous'),5200);
assert.equal(costPerItem(material,'previous'),1800000);assert.equal(costPhysicalRate(material).value,18000);assert.equal(costPhysicalRate(labor).value,6500);
assert.equal(costPhysicalRate({...material,kgPerUnit:0,quantityValue:0}).value,18000);assert.equal(costPhysicalRate({...labor,hoursPerUnit:null,current:null}).value,6500);
assert.equal(costPhysicalRate({...material,referenceBudget:0}).value,0);
assert.equal(costUnit({...labor,hoursPerUnit:0},'current'),null);
assert.equal(costUnitBasis({...labor,hoursPerUnit:null}).unit,'un');
assert.equal(costUnitBasis({...labor,hoursPerUnit:null}).pendingFactor,true);
assert.equal(costStats([material,labor]).current,14670000);
assert.equal(costPerUnit(material,'hoursPerUnit'),null);
`,scope);
'''
        result=subprocess.run(['node','-e',script],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
