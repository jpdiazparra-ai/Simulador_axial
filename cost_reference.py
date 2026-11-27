"""Read the published Costos sheet; retain source row numbers and missing values."""
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request
import streamlit as st

SOURCE_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQOSK1DE0sEuK5Cl-bIahOjtdP6qsBobzqSlekorQCY9gRpwhRDzHYxh9c-Q-mKoQ/pub?output=csv&gid=1070657893'
REQUIRED = ('ID', 'Hito objetivo', 'Capas del Archivo', 'Sistema', 'Paquete / línea', 'Actividad / entregable', 'Presupuesto vigente', 'Comercial anterior', 'Costo para producto')

def parse_money(value):
    value = value.strip().replace('\u00a0', '').replace(' ', '')
    if value in ('', '—', '–', '-', 'N/A'): return None
    if not re.fullmatch(r'-?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?', value):
        raise ValueError('Importe CLP no reconocido: ' + value)
    number = Decimal(value.replace('.', '').replace(',', '.'))
    if number != number.to_integral_value():
        raise ValueError('Se esperaba CLP entero: ' + value)
    return int(number)

def parse_quantity(value):
    """Interpret published decimal-comma quantities without inventing physical units."""
    value=value.strip().replace('\u00a0','').replace(' ','')
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?',value):return None
    number=Decimal(value.replace('.','').replace(',','.'))
    return int(number) if number==number.to_integral_value() else float(number)


def source_quantity(record, *names):
    fields={' '.join(str(key).split()).casefold():value for key,value in record.items()}
    for name in names:
        value=fields.get(name.casefold(),'')
        if str(value).strip():return parse_quantity(str(value))
    return None


def source_money(record, name):
    fields={' '.join(str(key).split()).casefold():value for key,value in record.items()}
    return parse_money(str(fields.get(name.casefold(),'') or ''))


def parse_cost_csv(raw, fetched_at=None):
    if isinstance(raw, bytes): raw = raw.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(raw)))
    header_i = next((i for i, row in enumerate(rows) if all(c in row for c in REQUIRED)), None)
    if header_i is None: raise ValueError('No se encontraron las columnas requeridas en Costos')
    header = rows[header_i]; records=[]; ids=set(); excluded=0
    for i, row in enumerate(rows[header_i+1:], header_i+2):
        d = dict(zip(header, row))
        ident = d.get('ID', '').strip()
        if not re.fullmatch(r'A\d+', ident): continue
        if ident in ids: raise ValueError('ID duplicado: '+ident)
        ids.add(ident)
        if d['Costo para producto'].strip().casefold() != 'aplica':
            excluded += 1; continue
        records.append({'id':ident, 'sourceRow':i, 'milestone':d['Hito objetivo'].strip(),
            'sourceLayer':d['Capas del Archivo'].strip(), 'system':d['Sistema'].strip(),
            'package':d['Paquete / línea'].strip(), 'activity':d['Actividad / entregable'].strip(),
            'criterion':d.get('Criterio','').strip(), 'quantity':d.get('Cantidad','').strip(),
            'quantityValue':parse_quantity(d.get('Cantidad','')),
            'hoursPerUnit':source_quantity(d,'Hrs por unidad','Horas por unidad','HH por unidad'),
            'kgPerUnit':source_quantity(d,'Kg por unidad','Kilogramos por unidad'),
            'hasPerUnitColumns':any(' '.join(field.split()).casefold() in ('hrs por unidad','horas por unidad','hh por unidad','kg por unidad','kilogramos por unidad') for field in header),
            'unit':next((d.get(field,'').strip() for field in ('Unidad de medida','Unidad','Unidad cantidad') if d.get(field,'').strip()),''),
            'referenceBudget':source_money(d,'Presupuesto referencia'),
            'current':parse_money(d['Presupuesto vigente']), 'previous':parse_money(d['Comercial anterior']),
            'applies':'Aplica', 'approved':d.get('Base aprobada','').strip()})
    if not records: raise ValueError('La fuente no contiene partidas Aplica')
    return {'metadata':{'url':SOURCE_URL,'sheet':'Costos','gid':'1070657893','currency':'CLP',
        'fetchedAt':fetched_at or datetime.now(timezone.utc).isoformat(),
        'sha256':hashlib.sha256(raw.encode('utf-8')).hexdigest(),
        'sourceRecords':len(ids),'included':len(records),'excluded':excluded,
        'defaultMilestone':'Producto 80 kW'},'rows':records}

@st.cache_data(ttl=300, show_spinner=False)
def load_cost_reference():
    try:
        request=urllib.request.Request(SOURCE_URL,headers={'User-Agent':'VAWT-cost-reference/1.0'})
        with urllib.request.urlopen(request, timeout=12) as response:
            raw=response.read(4_000_001)
        if len(raw)>4_000_000: raise ValueError('La respuesta supera el tamaño permitido')
        result=parse_cost_csv(raw);result['metadata'].update(status='live',unitFieldsVersion=3,referenceBudgetSource='Presupuesto referencia');return result
    except Exception:
        result=json.loads(Path(__file__).with_name('data').joinpath('cost_reference_snapshot.json').read_text())
        result['metadata']['status']='snapshot'
        return result
