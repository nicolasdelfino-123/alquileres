"""Read the client's XLSX as an archive; never execute formulas or create ledger entries."""
import calendar
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET
from zipfile import ZipFile, BadZipFile
from app.services.management_service import APIError

NS={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
MONTHS={'ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE'}


def safe_target(base,target):
    path=PurePosixPath(target.lstrip('/')) if target.startswith('/') else PurePosixPath(base)/target
    if '..' in path.parts:
        raise APIError('La planilla contiene una referencia no admitida')
    return str(path)


class Workbook:
    def __init__(self,path):
        try:
            self.zip=ZipFile(path)
            if len(self.zip.infolist())>3000 or sum(v.file_size for v in self.zip.infolist())>80*1024*1024:
                raise APIError('La planilla es demasiado grande')
            relationships=ET.fromstring(self.zip.read('xl/_rels/workbook.xml.rels'))
            rels={v.attrib['Id']:safe_target('xl',v.attrib['Target']) for v in relationships}
            workbook=ET.fromstring(self.zip.read('xl/workbook.xml'))
            self.sheets=[{'name':v.attrib['name'],'path':rels[v.attrib[REL]]} for v in workbook.find('x:sheets',NS)]
            self.strings=[]
            if 'xl/sharedStrings.xml' in self.zip.namelist():
                self.strings=[''.join(v.itertext()) for v in ET.fromstring(self.zip.read('xl/sharedStrings.xml')).findall('x:si',NS)]
            self.formats=[]
            if 'xl/styles.xml' in self.zip.namelist():
                styles=ET.fromstring(self.zip.read('xl/styles.xml'))
                custom={int(v.attrib['numFmtId']):v.attrib['formatCode'] for v in styles.findall('x:numFmts/x:numFmt',NS)}
                for style in styles.findall('x:cellXfs/x:xf',NS):
                    number=int(style.attrib.get('numFmtId',0));code=custom.get(number,'')
                    cleaned=re.sub(r'\[[^\]]*\]|"[^"]*"|\\.', '', code)
                    self.formats.append('date' if number in range(14,23) or re.search(r'[dy]',cleaned,re.I) else 'percent' if number in {9,10} or '%' in code else 'number')
        except (BadZipFile, KeyError, ET.ParseError, ValueError, OSError):
            raise APIError('No se pudo leer el Excel. Usá un archivo XLSX válido.',400) from None

    def close(self):
        self.zip.close()

    def value(self,cell):
        value=cell.find('x:v',NS)
        if cell.attrib.get('t')=='inlineStr':
            return ''.join(cell.find('x:is',NS).itertext())
        if value is None:
            return 'Sin resultado guardado' if cell.find('x:f',NS) is not None else ''
        raw=value.text or ''
        if cell.attrib.get('t')=='s':
            return self.strings[int(raw)]
        if cell.attrib.get('t') in {'str','e'}:
            return raw
        if cell.attrib.get('t')=='b':
            return 'Sí' if raw=='1' else 'No'
        try:
            number=Decimal(raw)
            if not number.is_finite():return raw
            index=int(cell.attrib.get('s','0'))
            kind=self.formats[index] if index<len(self.formats) else 'number'
            if kind=='date':return (datetime(1899,12,30)+timedelta(days=float(number))).strftime('%d/%m/%Y')
            if kind=='percent':return f'{number*100:.2f}%'
            return format(number,'f').rstrip('0').rstrip('.') if '.' in format(number,'f') else format(number,'f')
        except (InvalidOperation, ValueError, OverflowError):
            return raw

    def read(self,name):
        sheet=next((v for v in self.sheets if v['name']==name),None)
        if not sheet:raise APIError('Hoja no encontrada',404)
        doc=ET.fromstring(self.zip.read(sheet['path']))
        hyperlinks={}
        sheet_path=PurePosixPath(sheet['path'])
        rel_path=str(sheet_path.parent/'_rels'/(sheet_path.name+'.rels'))
        if rel_path in self.zip.namelist():
            related=ET.fromstring(self.zip.read(rel_path))
            targets={v.attrib.get('Id'):v.attrib.get('Target','') for v in related}
            for link in doc.findall('x:hyperlinks/x:hyperlink',NS):
                target=targets.get(link.attrib.get(REL),'')
                if target.startswith('https://'):
                    hyperlinks[link.attrib.get('ref')]=target
        raw={int(row.attrib['r']):{re.sub(r'\d','',c.attrib['r']):self.value(c) for c in row.findall('x:c',NS)} for row in doc.findall('x:sheetData/x:row',NS)}
        monthly=name.split(' ')[0] in MONTHS
        header_number=9 if monthly else 4 if name in {'ALERTAS','DEUDAS Y PENDIENTES','VENTAS','RESUMEN VENTAS'} else 13 if name=='DASHBOARD' else 3
        header=raw.get(header_number,{})
        columns=[key for key,value in header.items() if value.strip()]
        if not columns:
            columns=list(dict.fromkeys(key for row in raw.values() for key in row))[:30]
        # Keep the original order and labels, without inventing missing dates/people.
        headers=[{'key':key,'label':header.get(key,key).replace('\n',' ').strip()} for key in columns]
        rows=[];owner=''
        for number,row in raw.items():
            if number<=header_number:continue
            if monthly:
                label=row.get('B','').strip().lstrip('▶► ').strip()
                address=row.get('C','').strip()
                if label and not address and not label.startswith(('SUBTOTAL','TOTAL')):
                    owner=label
                if not address or address.startswith(('SUBTOTAL','TOTAL')):continue
                row['B']=label or owner
            if not any(row.get(key,'').strip() for key in columns):continue
            rows.append({'row':number,'values':{key:row.get(key,'') for key in columns},'links':{key:hyperlinks[f'{key}{number}'] for key in columns if f'{key}{number}' in hyperlinks}})
        return {'name':name,'headers':headers,'rows':rows,'monthly':monthly,'source':'Excel original de Bricks Bienes Raíces. Consulta sin registrar movimientos nuevos.'}
