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
const helpers=source.slice(source.indexOf('function costKind('),source.indexOf('function costNavigation('));
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
