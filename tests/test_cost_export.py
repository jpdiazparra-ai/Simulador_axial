"""Offline HTML exports preserve financial scope and safely embed source text."""
import subprocess
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NODE='/Users/jonathan.diaz/.nvm/versions/node/v24.18.0/bin/node'

class CostExportTests(unittest.TestCase):
    def test_total_filtered_missing_values_and_safe_report(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const scope={f:(v,n)=>Number.isFinite(v)?v.toFixed(n):'—',console};vm.createContext(scope);
vm.runInContext(fs.readFileSync('assets/cost_dashboard.js','utf8'),scope);
vm.runInContext(fs.readFileSync('assets/cost_export.js','utf8'),scope);
vm.runInContext(`
const IFCView={offer:'A'},CostPreview={sourceKey:null};
CostView.data={metadata:{sheet:'Costos',status:'snapshot'},rows:[
{id:'A1',milestone:'Producto 80 kW',sourceLayer:'Rotor',package:'Aspa',activity:'Pala',current:9800,previous:7840},
{id:'A2',milestone:'Producto 80 kW',sourceLayer:'Rotor',package:'Carenado',activity:'Peso',current:null,previous:0},
{id:'A3',milestone:'Producto 80 kW',sourceLayer:'Torre',package:'Torre',activity:'Torre',current:1960,previous:980},
{id:'A4',milestone:'Otro proyecto',sourceLayer:'Rotor',package:'Aspa',activity:'Otro',current:999999,previous:999999}]};
let all=costAnalysisSnapshot();
if(all.tableRows.length!==3||all.contextCount!==3||all.tableStats.current!==11760)throw Error('total scope');
if(all.tableRows.some(r=>r.id==='A4'))throw Error('unrelated project included');
CostView.layer='Rotor';CostView.package='Aspa';let selected=costAnalysisSnapshot();
if(selected.tableRows.length!==1||selected.tableRows[0].id!=='A1'||selected.contextCount!==2)throw Error('package/table versus layer/chart scope');
if(selected.contextRows.length!==2||selected.contextRows.some(r=>r.sourceLayer!=='Rotor')||selected.contextRows.some(r=>r.milestone!=='Producto 80 kW'))throw Error('offline navigation scope leaks unrelated rows');
if(selected.contextRows.find(r=>r.id==='A2').current!==null||selected.contextRows.find(r=>r.id==='A2').previous!==0)throw Error('offline navigation must preserve missing and zero separately');
if(selected.state.fxRate!==980||selected.tableStats.current!==9800)throw Error('exchange rate or source amounts changed');
CostView.activity='A2';CostView.package='Carenado';let missing=costAnalysisSnapshot();
if(missing.tableStats.currentCount!==0||missing.tableStats.previousCount!==1)throw Error('missing became zero');
CostView.layer='all';CostView.package='all';CostView.activity='all';CostView.search='does-not-exist';if(costAnalysisSnapshot().tableRows.length!==0)throw Error('empty search ignored');
CostView.search='';CostView.data.rows[0].package='<script>alert(1)</script>';let safe=costAnalysisSnapshot();
const html=costExportDocument(safe,'body{margin:0}','<section id="step-6">Informe</section>');
if(html.includes('<script>alert(1)</script>'))throw Error('unescaped source label');
if(!html.includes('\\\\u003cscript')||!html.includes('cost-analysis-snapshot'))throw Error('unsafe JSON data');
if(!html.includes('1 USD = 980.00 CLP')||!html.includes('3 partidas en la tabla'))throw Error('missing scope or currency');
const rows=costExportBoardRows(safe);if(rows.includes('NaN')||rows.includes('Infinity'))throw Error('invalid bar scale');
if(!rows.includes('US$ 10.00'))throw Error('USD must be converted once');
CostView.data.rows=[{id:'zero',milestone:'Producto 80 kW',sourceLayer:'Cero',package:'Cero',current:0,previous:0}];
if(costExportBoardRows(costAnalysisSnapshot()).includes('NaN'))throw Error('zero scale');
`,scope);
'''
        result=subprocess.run([NODE,'-e',script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_export_table_keeps_native_scrolling_and_pinned_edges(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const scope={};vm.createContext(scope);vm.runInContext(fs.readFileSync('assets/cost_export.js','utf8'),scope);
const rows=Array.from({length:60},(_,index)=>({id:index}));
const wrap={style:{},setAttribute(key,value){this[key]=value;},addEventListener(){throw Error('must not capture wheel or pointer gestures');}};
const table={tBodies:[{rows}],closest:()=>wrap,addEventListener(){throw Error('table must retain native scrolling');}};
scope.initCostExportTableViewport({getElementById:()=>table});
assert.equal(rows.length,60);assert.equal(wrap.tabIndex,0);assert(wrap['aria-label'].includes('encabezado, totales'));assert.equal(wrap.style.maxHeight,undefined,'CSS controls the viewport, without a 44-row override');
const snapshot={generatedAt:'2026-11-26T15:00:00Z',state:{milestone:'Producto 80 kW',layer:'all',package:'all',activity:'all',fxRate:980},tableRows:[],contextCount:0,variant:'A'};
scope.f=(v,n)=>v.toFixed(n);const report=scope.costExportDocument(snapshot,'','<table id="cost-table"></table>');
assert(report.includes('max-height:min(70vh,650px)'));assert(report.includes('overscroll-behavior:auto'));assert(!report.includes('rowLimit=44'));
assert(report.includes('#cost-table thead th{position:sticky;top:0;'));assert(report.includes('#cost-table tfoot td{position:sticky;bottom:0;'));
assert(report.includes('#cost-table tbody td:first-child{position:sticky;left:0;'));assert(report.includes('#cost-table tbody td:last-child{position:sticky;right:0;'));
'''
        result=subprocess.run([NODE,'-e',script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_export_preserves_both_interactive_kpi_labels_values_and_notes(self):
        script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');const scope={};vm.createContext(scope);vm.runInContext(fs.readFileSync('assets/cost_export.js','utf8'),scope);
const makeKpi=(label,value)=>({className:'metric-card cost-kpi current',classList:{contains:name=>name==='cost-kpi'},childNodes:[{tagName:'SPAN',className:'cost-kpi-tag',textContent:'DETALLE'},{tagName:'SPAN',className:'cost-kpi-label',textContent:label},{tagName:'STRONG',textContent:value},{tagName:'SMALL',textContent:'5 de 6 partidas con importe'}],replaceWith(node){this.replacement=node;}});
const buttons=[makeKpi('Costo al detalle · USD','US$ 9.726,53'),makeKpi('Costo por mayor · USD','US$ 6.606,57')];
const doc={createElement:tag=>({tagName:tag.toUpperCase(),children:[],append(...children){this.children.push(...children);}})};
scope.costExportFreezeButtons({querySelectorAll:()=>buttons},doc);
for(const button of buttons){const output=button.replacement;assert.equal(output.tagName,'DIV');assert.equal(output.children.length,4);assert.strictEqual(output.children[2],button.childNodes[2],'formatted value element must be preserved, not flattened into text');assert.equal(output.children[2].tagName,'STRONG');assert(output.children[3].textContent.includes('5 de 6'));}
'''
        result=subprocess.run([NODE,'-e',script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
