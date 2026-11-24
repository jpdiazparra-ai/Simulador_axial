import csv
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from cost_reference import parse_money, parse_cost_csv, load_cost_reference, REQUIRED

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
