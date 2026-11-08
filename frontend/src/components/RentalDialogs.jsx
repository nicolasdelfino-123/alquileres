import MessageDocuments from './MessageDocuments';
import { useRef, useState } from 'react';
import { Check, Download, MessageCircle, Paperclip, Printer } from 'lucide-react';
import { api, documentApi, downloadDocument, financeApi } from '../lib/api';
import { dateLabel, money, MONTHS, personName, decimalInput } from '../lib/format';
import Dialog from './Dialog';
import { Alert, Button, Field, inputClasses } from './ui';
import { DetailFields, FormShell, TextField } from './EntityUI';

export const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Argentina/Cordoba', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
export const paymentMethods = { transfer: 'Transferencia', cash: 'Efectivo', deposit: 'Depósito', other: 'Otro' };
export const rentStates = {
  not_generated: { label: 'Sin generar', classes: 'bg-slate-100 text-slate-600 ring-slate-600/10' },
  pending: { label: 'Pendiente', classes: 'bg-amber-50 text-amber-800 ring-amber-600/10' },
  overdue: { label: 'Vencido', classes: 'bg-red-50 text-red-700 ring-red-600/10' },
  partial: { label: 'Pago parcial', classes: 'bg-orange-50 text-orange-700 ring-orange-600/10' },
  paid: { label: 'Cobrado', classes: 'bg-emerald-50 text-emerald-700 ring-emerald-600/10' },
  transferred: { label: 'Transferido', classes: 'bg-emerald-50 text-emerald-700 ring-emerald-600/10' },
  cancelled: { label: 'Anulado', classes: 'bg-slate-100 text-slate-500 ring-slate-600/10' },
};
export const propertyLabel = (property) => property ? `${property.address}${property.unit ? ` · ${property.unit}` : ''}` : 'Propiedad no disponible';
export function Metrics({ items }) {
  return <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{items.map(([label, value, detail]) => <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs"><p className="text-xs font-medium text-muted">{label}</p><p className="mt-3 break-words text-2xl font-semibold tracking-tight">{value}</p>{detail && <p className="mt-2 text-[11px] text-muted">{detail}</p>}</div>)}</div>;
}

export function MoneyOperation({ kind, charge, settlement, property, owner, year, month, currency, onClose, onSaved }) {
  const limit = kind === 'payment' ? charge.outstanding_balance : kind === 'transfer' ? settlement.outstanding_balance : '';
  const [values, setValues] = useState({ amount: limit, date: today(), method: 'transfer', reference: '', notes: '', deductions: '' });
  const [key] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const props = (name) => ({ value: values[name], disabled: busy, onChange: (event) => setValues({ ...values, [name]: event.target.value }) });
  const submit = async (event) => {
    event.preventDefault(); if (busy) return;
    const amount = decimalInput(values.amount);
    if (kind !== 'settlement' && (amount === null || Number(amount) <= 0)) { setError('Ingresá un importe mayor a cero, sin separadores de miles.'); return; }
    const deductions = values.deductions === '' ? '0' : decimalInput(values.deductions);
    if (deductions === null) { setError('Revisá el importe de deducciones.'); return; }
    const base = { idempotency_key: key, notes: values.notes.trim() || null };
    setBusy(true); setError('');
    try {
      let result;
      if (kind === 'payment') result = await financeApi.payment({ ...base, contract_id: charge.contract_id, charge_id: charge.id, amount, payment_date: values.date, payment_method: values.method, reference: values.reference.trim() || `COBRO-${key}` });
      else if (kind === 'transfer') result = await financeApi.transfer({ ...base, settlement_id: settlement.id, amount, transfer_date: values.date, payment_method: values.method, reference: values.reference.trim() || `TRANSF-${key}` });
      else result = await financeApi.settlement({ ...base, property_id: property.id, owner_id: owner.id, period_year: Number(year), period_month: Number(month), currency, settlement_date: values.date, deductions });
      onSaved(result);
    } catch (failure) { setError(failure.message); } finally { setBusy(false); }
  };
  const titles = { payment: 'Registrar cobro', settlement: 'Liquidar al propietario', transfer: 'Registrar transferencia' };
  return <FormShell title={titles[kind]} onClose={onClose} onSubmit={submit} busy={busy} error={error} intro={kind === 'settlement' ? 'Se calcula sobre lo efectivamente cobrado y todavía no liquidado, respetando la participación del propietario y los honorarios del contrato.' : 'Registrá el movimiento real. El saldo se actualiza con el importe recibido o transferido; no se marca como pagado sin un movimiento.'} submitLabel={titles[kind]}>
    <p className="text-sm font-semibold">{propertyLabel(property)}{owner && <span className="mt-1 block font-normal text-muted">{personName(owner)}</span>}</p>
    {kind !== 'settlement' && <><p className="rounded-xl bg-emerald-50 p-3 text-sm text-brand">Saldo disponible: {money(limit, currency)}</p><TextField id="movement-amount" label="Importe *" required inputMode="decimal" {...props('amount')} /></>}
    <TextField id="movement-date" label="Fecha *" type="date" max={today()} required {...props('date')} />
    {kind === 'settlement' ? <TextField id="settlement-deductions" label="Gastos / deducciones a descontar (opcional)" inputMode="decimal" hint="Las expensas o gastos cargados por separado no se descuentan automáticamente. Ingresá únicamente lo que corresponde descontar en esta liquidación." {...props('deductions')} /> : <><Field id="movement-method" label="Medio de pago"><select id="movement-method" className={inputClasses} {...props('method')}>{Object.entries(paymentMethods).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></Field><TextField id="movement-reference" label="Número de operación / referencia (opcional)" maxLength={150} {...props('reference')} /></>}
    {owner && <div className="rounded-xl border border-slate-200 p-4 text-xs leading-6 text-muted"><p>Alias: <strong className="text-ink">{owner.bank_alias || 'Sin cargar'}</strong></p><p>CBU: <strong className="break-all text-ink">{owner.cbu || 'Sin cargar'}</strong></p><p>Titular: {owner.bank_holder || personName(owner)}</p></div>}
    <Field id="movement-notes" label="Observaciones"><textarea id="movement-notes" rows={3} className={inputClasses} {...props('notes')} /></Field>
  </FormShell>;
}

export function AdjustmentDialog({ contract, property, onClose, onSaved }) {
  const [mode, setMode] = useState(['IPC','ICL'].includes(contract.adjustment_index) ? contract.adjustment_index : 'percentage');
  const [values, setValues] = useState({ effective_date: contract.next_adjustment_date || `${today().slice(0,7)}-01`, percentage: contract.fixed_adjustment_percentage || '', new_amount: '', index_start: '', index_end: '', monthly: '', notes: '', source_url: contract.adjustment_index === 'IPC' ? 'https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31' : 'https://www.bcra.gob.ar/tasas-de-interes/' });
  const [busy,setBusy] = useState(false), [error,setError] = useState('');
  const props = (name) => ({ value:values[name], disabled:busy, onChange:(event)=>setValues({...values,[name]:event.target.value}) });
  const rates = values.monthly.split(/[;\n]+/).map((value)=>value.trim()).filter(Boolean);
  let estimate = Number(contract.current_rent);
  if (mode === 'amount') estimate = Number(values.new_amount.replace(',','.'));
  if (mode === 'percentage') estimate *= 1+Number(String(values.percentage).replace(',','.'))/100;
  if (mode === 'ICL') estimate *= Number(values.index_end.replace(',','.'))/Number(values.index_start.replace(',','.'));
  if (mode === 'IPC') for (const rate of rates) estimate *= 1+Number(rate.replace(',','.'))/100;
  const submit = async (event) => {
    event.preventDefault(); if(busy) return; setBusy(true); setError('');
    try { const body={ mode, effective_date:values.effective_date, notes:values.notes || null, source_url:values.source_url || null };
      if(mode==='IPC') body.monthly_percentages=rates.map((value)=>value.replace(',','.'));
      if(mode==='ICL') { body.index_start=values.index_start.replace(',','.'); body.index_end=values.index_end.replace(',','.'); }
      if(mode==='amount') body.new_amount=values.new_amount.replace(',','.');
      if(mode==='percentage') body.percentage=String(values.percentage).replace(',','.');
      onSaved(await financeApi.adjust(contract.id,body));
    } catch(failure) { setError(failure.message); } finally { setBusy(false); }
  };
  return <FormShell title="Aplicar aumento" onSubmit={submit} onClose={onClose} busy={busy} error={error} submitLabel="Confirmar aumento" intro="El aumento queda registrado con su cálculo y fuente. No modifica mensualidades ya generadas ni pagos anteriores.">
    <p className="text-sm font-semibold">{propertyLabel(property)}</p><p className="text-sm text-muted">Alquiler vigente: {money(contract.current_rent,contract.currency)}</p>
    <TextField id="adjust-date" label="Aplicar desde *" type="date" required {...props('effective_date')} />
    <Field id="adjust-mode" label="Método de cálculo"><select id="adjust-mode" className={inputClasses} disabled={busy} value={mode} onChange={(event)=>setMode(event.target.value)}><option value="IPC">IPC · variaciones mensuales</option><option value="ICL">ICL · cociente de índices</option><option value="percentage">Porcentaje pactado</option><option value="amount">Nuevo importe acordado</option></select></Field>
    {mode==='IPC' && <Field id="adjust-months" label="IPC de cada mes (%) *" hint="Una variación por línea o separadas por punto y coma. Se acumulan multiplicando, no sumando. No hay sincronización automática: copiá los valores publicados por INDEC."><textarea id="adjust-months" className={inputClasses} required rows={4} placeholder={'2,5; 2,1; 1,9'} {...props('monthly')} /></Field>}
    {mode==='ICL' && <div className="grid gap-4 sm:grid-cols-2"><TextField id="adjust-index-start" label="ICL al inicio del período *" inputMode="decimal" required {...props('index_start')} /><TextField id="adjust-index-end" label="ICL al final del período *" inputMode="decimal" required {...props('index_end')} /></div>}
    {mode==='percentage' && <TextField id="adjust-percentage" label="Aumento (%) *" inputMode="decimal" required {...props('percentage')} />}
    {mode==='amount' && <TextField id="adjust-amount" label="Nuevo alquiler *" inputMode="decimal" required {...props('new_amount')} />}
    <div className="rounded-xl bg-emerald-50 p-4"><p className="text-xs text-brand">Estimación sobre el alquiler vigente</p><p className="mt-2 text-2xl font-semibold text-brand">{Number.isFinite(estimate) && estimate>=0 ? money(estimate,contract.currency) : 'Completá los valores'}</p><p className="mt-2 text-xs text-muted">El importe definitivo se valida con el historial al guardar.</p></div>
    <TextField id="adjust-source" label="Fuente / referencia (opcional)" type="url" {...props('source_url')} />
    <Field id="adjust-notes" label="Observaciones"><textarea id="adjust-notes" rows={2} className={inputClasses} {...props('notes')} /></Field>
  </FormShell>;
}

export function MessageDialog({ contract, property, tenant, owner, charge, year, month, onClose }) {
  const [selectedDocuments,setSelectedDocuments]=useState([]);
  const [template,setTemplate] = useState('collection'), [target,setTarget] = useState('tenant');
  const [custom,setCustom] = useState(null), [phone,setPhone] = useState(null), [error,setError]=useState('');
  const [channel,setChannel]=useState('whatsapp'),[scheduleAt,setScheduleAt]=useState(''),[sending,setSending]=useState(false),[notice,setNotice]=useState('');
  const recipient=target==='tenant'?tenant:owner;
  const name=personName(recipient), period=`${MONTHS[month-1]} ${year}`;
  const amount=charge?.outstanding_balance ?? contract.current_rent;
  const templates={
    collection:`Hola ${name}, te recordamos el alquiler de ${propertyLabel(property)}, correspondiente a ${period}.\nImporte pendiente: ${money(amount,contract.currency)}.${charge?.due_date ? `\nVencimiento: ${dateLabel(charge.due_date)}.` : ''}${contract.collection_alias ? `\nAlias: ${contract.collection_alias}.` : ''}${contract.collection_cbu ? `\nCBU: ${contract.collection_cbu}.` : ''}\nPor favor, envianos el comprobante al realizar el pago.\n\nSaludos, Bricks Bienes Raíces.`,
    adjustment:`Hola ${name}, te avisamos que el contrato de ${propertyLabel(property)} tiene prevista su actualización${contract.next_adjustment_date?` el ${dateLabel(contract.next_adjustment_date)}`:''}${contract.adjustment_index?` según ${contract.adjustment_index}`:''}.\nEl alquiler vigente es ${money(contract.current_rent,contract.currency)}. Te informaremos el nuevo importe una vez confirmado el cálculo.\n\nSaludos, Bricks Bienes Raíces.`,
    expiration:`Hola ${name}, el contrato de ${propertyLabel(property)} finaliza el ${dateLabel(contract.end_date)}. Contactanos para coordinar los próximos pasos.\n\nSaludos, Bricks Bienes Raíces.`,
    owner:`Hola ${name}, contactanos para consultar la liquidación de ${propertyLabel(property)} correspondiente a ${period} y coordinar el pago.\n\nSaludos, Bricks Bienes Raíces.`,
  };
  const text=custom??templates[template];
  const outgoingText=text+(selectedDocuments.length?'\n\nComprobantes: '+selectedDocuments.map(document=>document.original_filename).join(', '):'');
  const open=()=>{const digits=(phone??recipient?.phone??'').replace(/\D/g,'');if(!/^\d{11,15}$/.test(digits)){setError('Completá el teléfono con código de país y área, sin el 0 ni el 15. Ejemplo: 5493511234567.');return;}window.open(`https://wa.me/${digits}?text=${encodeURIComponent(outgoingText)}`,'_blank','noopener,noreferrer');};
  const schedule=async()=>{if(sending)return;setSending(true);setError('');setNotice('');try{await api(`/contracts/${contract.id}/messages`,{method:'POST',body:{person_id:recipient?.id,message:outgoingText,document_ids:selectedDocuments.map(document=>document.id),scheduled_at:scheduleAt?new Date(scheduleAt).toISOString():new Date().toISOString()}});setNotice('Mensaje guardado en la cola de envío por correo. Se enviará automáticamente en la fecha indicada; revisá su estado en la ficha del contrato.');}catch(failure){setError(failure.message);}finally{setSending(false);}};
  return <Dialog title="Preparar aviso de alquiler" size="lg" onClose={onClose}><div className="space-y-5 p-6">{error&&<Alert>{error}</Alert>}{notice&&<Alert type="success">{notice}</Alert>}<Field id="message-channel" label="Canal"><select id="message-channel" className={inputClasses} value={channel} onChange={(event)=>setChannel(event.target.value)}><option value="whatsapp">WhatsApp · revisar y enviar</option><option value="email">Correo · envío automático o programado</option></select></Field><div className="grid gap-4 sm:grid-cols-2"><Field id="message-template" label="Plantilla"><select id="message-template" className={inputClasses} value={template} onChange={(event)=>{setTemplate(event.target.value);setCustom(null);}}><option value="collection">Recordatorio de pago</option><option value="adjustment">Próximo aumento</option><option value="expiration">Vencimiento de contrato</option><option value="owner">Consulta de liquidación</option></select></Field><Field id="message-target" label="Destinatario"><select id="message-target" className={inputClasses} value={target} onChange={(event)=>{setTarget(event.target.value);setCustom(null);setPhone(null);setSelectedDocuments([]);}}><option value="tenant">Inquilino · {personName(tenant)}</option>{owner&&<option value="owner">Propietario · {personName(owner)}</option>}</select></Field></div>{channel==='whatsapp'?<TextField id="message-phone" label="WhatsApp con código de país" value={phone??recipient?.phone??''} onChange={(event)=>setPhone(event.target.value)} placeholder="5493511234567" />:<><p className="text-sm text-muted">Destinatario: <strong>{recipient?.email||'Falta cargar el correo en su ficha'}</strong></p><TextField id="message-schedule" label="Fecha y hora de envío · vacío para enviar ahora" type="datetime-local" value={scheduleAt} onChange={(event)=>setScheduleAt(event.target.value)}/></>}<MessageDocuments contract={contract} property={property} recipient={recipient} year={year} month={month} selected={selectedDocuments} onSelect={setSelectedDocuments} channel={channel} message={outgoingText}/><Field id="message-body" label="Mensaje"><textarea id="message-body" rows={10} className={inputClasses} value={text} onChange={(event)=>setCustom(event.target.value)} /></Field><p className="text-xs leading-6 text-muted">{channel==='whatsapp'?'Los datos se completan desde el contrato. El envío se confirma en WhatsApp; no hay envío automático por WhatsApp conectado.':'El sistema enviará este aviso por correo automáticamente. Requiere el remitente configurado y el backend en funcionamiento.'}</p><div className="flex justify-end gap-3"><Button variant="secondary" onClick={onClose} disabled={sending}>Cerrar</Button>{channel==='whatsapp'?<Button onClick={open}><MessageCircle size={17}/>Abrir WhatsApp</Button>:<Button onClick={schedule} disabled={sending||!recipient?.email||!!notice}>{sending?'Programando…':scheduleAt?'Programar envío':'Enviar por correo'}</Button>}</div></div></Dialog>;
}

export function DocumentDialog({ property, contract, charge, payment, settlement, transfer, year, month, onClose, onSaved }) {
  const [period,setPeriod]=useState(()=>{const y=year||charge?.period_year||settlement?.period_year,m=month||charge?.period_month||settlement?.period_month;return y&&m?`${y}-${String(m).padStart(2,'0')}`:today().slice(0,7);});
  const [file,setFile]=useState(null),[link,setLink]=useState(''),[type,setType]=useState(payment?'Comprobante de cobro':transfer?'Comprobante de transferencia':settlement?'Liquidación':'Comprobante de gasto'),[notes,setNotes]=useState('');
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const submit=async(event)=>{event.preventDefault();if(busy)return;setBusy(true);setError('');try{const fields={document_type:type,...(period?{period_year:Number(period.slice(0,4)),period_month:Number(period.slice(5,7))}:{}),...(charge?{charge_id:charge.id}:{}), ...(property?{property_id:property.id}:{}),...(contract?{contract_id:contract.id}:{}),...(payment?{payment_id:payment.id,charge_id:payment.charge_id}:{}),...(settlement?{settlement_id:settlement.id}:{}),...(transfer?{transfer_id:transfer.id}:{}),...(notes?{notes}:{} )};let result;if(file){const form=new FormData();Object.entries(fields).forEach(([k,v])=>form.append(k,v));form.append('file',file);result=await documentApi.upload(form);}else{if(!link.startsWith('https://'))throw new Error('Adjuntá un archivo o un enlace HTTPS válido.');result=await documentApi.link({...fields,file_path:link,original_filename:type});}onSaved(result);}catch(failure){setError(failure.message);}finally{setBusy(false);}};
  return <FormShell title="Agregar comprobante o documento" onClose={onClose} onSubmit={submit} busy={busy} error={error} submitLabel="Guardar documento"><TextField id="document-period" label="Mes al que corresponde" type="month" value={period} disabled={busy} onChange={event=>setPeriod(event.target.value)}/><p className="text-xs text-muted">Dejá el mes vacío si es un documento general del contrato.</p><TextField id="document-type" label="Tipo de documento" value={type} required maxLength={100} disabled={busy} onChange={(event)=>setType(event.target.value)}/><Field id="document-file" label="Archivo PDF, JPG o PNG (hasta 10 MB)"><input id="document-file" type="file" accept="application/pdf,image/png,image/jpeg" disabled={busy} onChange={(event)=>setFile(event.target.files[0]||null)} className={inputClasses}/></Field>{!file&&<TextField id="document-link" label="O enlace a Drive / comprobante" type="url" value={link} disabled={busy} onChange={(event)=>setLink(event.target.value)} placeholder="https://…"/>}<Field id="document-notes" label="Observaciones"><textarea id="document-notes" className={inputClasses} rows={2} value={notes} disabled={busy} onChange={(event)=>setNotes(event.target.value)}/></Field></FormShell>;
}

export function DocumentList({ documents }) {
  const [error,setError]=useState('');
  return <div>{error&&<Alert>{error}</Alert>}{!documents.length?<p className="py-5 text-sm text-muted">Todavía no hay documentos vinculados.</p>:<ul className="divide-y divide-slate-100">{documents.map((document)=><li key={document.id} className="flex items-center justify-between gap-3 py-4"><div><p className="text-sm font-medium">{document.document_type}</p><p className="mt-1 break-all text-xs text-muted">{document.original_filename}</p>{document.period_year&&<p className="mt-1 text-xs text-muted">{MONTHS[document.period_month-1]} {document.period_year}</p>}{document.notes&&<p className="mt-1 text-xs text-muted">{document.notes}</p>}</div><Button variant="ghost" onClick={async()=>{try{await downloadDocument(document);}catch(failure){setError(failure.message);}}}><Download size={16}/>Abrir</Button></li>)}</ul>}</div>;
}

export function printElement(element, title) {const safeTitle=String(title).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');const frame=document.createElement('iframe');frame.style.cssText='position:fixed;width:0;height:0;border:0;';document.body.appendChild(frame);const doc=frame.contentDocument;doc.open();doc.write(`<!doctype html><html lang="es"><head><title>${safeTitle}</title><style>body{font-family:Arial,sans-serif;color:#172b29;padding:36px;font-size:13px}h1{font-size:26px}table{width:100%;border-collapse:collapse;margin:28px 0}td,th{text-align:left;padding:12px 0;border-bottom:1px solid #ddd}.text-right{text-align:right}.font-semibold{font-weight:600}.text-xs{font-size:11px}.text-muted{color:#667}.mt-2{margin-top:8px}.mt-6{margin-top:24px}.mt-10{margin-top:40px}.whitespace-pre-wrap{white-space:pre-wrap}.border-t{border-top:1px solid #ddd}.pt-4{padding-top:16px}.text-2xl{font-size:24px}.uppercase{text-transform:uppercase}.tracking-widest{letter-spacing:2px}</style></head><body>${element.innerHTML}</body></html>`);doc.close();frame.contentWindow.focus();frame.contentWindow.print();setTimeout(()=>frame.remove(),60000);};

export { default as ReceiptDialog } from './EditableReceiptDialog';

export function OwnerStatementDialog({ owner, settlements, properties, year, month, currency, onClose }) {
  const ref=useRef(null);
  const total=(key)=>settlements.reduce((sum,row)=>sum+Number(row[key]),0);
  return <Dialog title="Liquidación consolidada por propietario" size="xl" onClose={onClose}><div className="space-y-5 bg-slate-50 p-6"><div ref={ref} className="rounded-xl border border-slate-200 bg-white p-7"><p className="text-xs font-semibold tracking-widest text-brand uppercase">Bricks Bienes Raíces</p><h1 className="mt-2 text-2xl font-semibold">Liquidación a propietario</h1><p className="mt-6 text-sm"><strong>{personName(owner)}</strong> · {MONTHS[month-1]} {year}</p><p className="mt-2 text-xs text-muted">Alias: {owner?.bank_alias||'Sin cargar'} · CBU: {owner?.cbu||'Sin cargar'}</p><div className="mt-6 overflow-x-auto"><table className="w-full text-sm"><thead><tr>{['Inmueble','Bruto','Honorarios','Gastos','Neto','Transferido'].map((label)=><th key={label} className="border-b border-slate-200 px-2 py-3 text-left">{label}</th>)}</tr></thead><tbody>{settlements.map((record)=><tr key={record.id}><td className="border-b border-slate-100 px-2 py-3">{propertyLabel(properties.find((p)=>p.id===record.property_id))}<p className="mt-1 text-xs text-muted">Liquidación #{record.id}</p></td>{['gross_amount','administration_fee','deductions','net_amount','transferred_amount'].map((key)=><td key={key} className="whitespace-nowrap border-b border-slate-100 px-2 py-3">{money(record[key],currency)}</td>)}</tr>)}</tbody></table></div><p className="mt-6 text-right text-lg font-semibold">Neto liquidado: {money(total('net_amount'),currency)}</p><p className="mt-2 text-right text-sm">Pendiente de transferir: {money(total('outstanding_balance'),currency)}</p><p className="mt-10 border-t border-dashed border-slate-300 pt-4 text-xs text-muted">Firma y aclaración</p><p className="mt-6 text-xs text-muted">Resumen de liquidaciones registradas. La transferencia se acredita mediante sus movimientos y comprobantes.</p></div><div className="flex justify-end gap-3"><Button variant="secondary" onClick={onClose}>Cerrar</Button><Button onClick={()=>printElement(ref.current,'Liquidación consolidada')}><Printer size={16}/>Imprimir / guardar PDF</Button></div></div></Dialog>;
}

export function BulkSettlementDialog({ owner, data, year, month, currency, onClose, onSaved }) {
  const [key]=useState(()=>crypto.randomUUID()),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const properties=data.owners.filter((link)=>link.person_id===owner.id).map((link)=>data.properties.find((property)=>property.id===link.property_id));
  const submit=async(event)=>{event.preventDefault();if(busy)return;setBusy(true);setError('');try{await api('/settlements/generate-owner',{method:'POST',body:{owner_id:owner.id,year,month,currency,idempotency_key:key}});onSaved();}catch(failure){setError(failure.message);}finally{setBusy(false);}};
  return <FormShell title="Liquidar cobros del propietario" onSubmit={submit} onClose={onClose} busy={busy} error={error} submitLabel="Confirmar liquidaciones" intro="Se liquidará únicamente el dinero ya cobrado y disponible de este período, según la participación del propietario y el porcentaje de honorarios de cada mensualidad. No se duplican liquidaciones. No se agregan deducciones en esta operación masiva; si necesitás descontar gastos, usá la liquidación individual."><p className="font-semibold">{personName(owner)} · {MONTHS[month-1]} {year} · {currency}</p><ul className="space-y-3 text-sm text-muted">{properties.map((property)=><li key={property.id}>{propertyLabel(property)}</li>)}</ul><p className="text-xs leading-6 text-muted">Los inmuebles sin cobros disponibles se omiten. Esta operación registra las liquidaciones y no realiza transferencias bancarias.</p></FormShell>;
}

export function ChargeDialog({ contract, property, charge, year, month, onClose, onSaved }) {
  const [values,setValues]=useState({rent_amount:charge?.rent_amount??'',other_charges:charge?.other_charges||'',discounts:charge?.discounts||'',due_date:charge?.due_date||`${year}-${String(month).padStart(2,'0')}-${String(Math.min(contract.payment_day||10,new Date(year,month,0).getDate())).padStart(2,'0')}`,notes:charge?.notes||'',reason:''});
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const props=(name)=>({value:values[name],disabled:busy,onChange:(event)=>setValues({...values,[name]:event.target.value})});
  const submit=async(event)=>{event.preventDefault();if(busy)return;const body={...(values.rent_amount!==''?{rent_amount:decimalInput(values.rent_amount)}:{}),other_charges:values.other_charges===''?'0':decimalInput(values.other_charges),discounts:values.discounts===''?'0':decimalInput(values.discounts),due_date:values.due_date,notes:values.notes.trim()||null};if([body.rent_amount,body.other_charges,body.discounts].some((v)=>v===null)){setError('Revisá los importes: hasta dos decimales, sin separadores de miles.');return;}setBusy(true);setError('');try{const saved=charge?await api(`/charges/${charge.id}/correct`,{method:'POST',body:{...body,reason:values.reason}}):await api('/charges',{method:'POST',body:{...body,contract_id:contract.id,period_year:year,period_month:month}});onSaved(saved);}catch(failure){setError(failure.message);}finally{setBusy(false);}};
  const total=Number(String(values.rent_amount).replace(',','.'))+Number(String(values.other_charges).replace(',','.'))-Number(String(values.discounts).replace(',','.'));
  return <FormShell title={charge?'Corregir mensualidad sin movimientos':'Crear mensualidad'} onClose={onClose} onSubmit={submit} busy={busy} error={error} submitLabel="Guardar mensualidad" intro={charge?'Solo se puede corregir antes de registrar cobros o liquidaciones. Se guarda el motivo y el historial del cambio.':'Alquiler, cargos adicionales y descuentos se registran por separado. El cobro se carga después.'}><p className="text-sm font-semibold">{propertyLabel(property)} · {MONTHS[month-1]} {year}</p><TextField id="charge-rent" label="Alquiler · vacío para calcular según historial" placeholder="Automático según contrato y aumentos" inputMode="decimal" required={Boolean(charge)} {...props('rent_amount')}/><div className="grid gap-4 sm:grid-cols-2"><TextField id="charge-extras" label="Cargos adicionales · opcional" inputMode="decimal" {...props('other_charges')}/><TextField id="charge-discounts" label="Descuentos · opcional" inputMode="decimal" {...props('discounts')}/></div><TextField id="charge-due" label="Vencimiento *" type="date" required {...props('due_date')}/><p className="rounded-xl bg-emerald-50 p-4 text-lg font-semibold text-brand">{values.rent_amount===''?'Alquiler automático + cargos − descuentos':`Total: ${Number.isFinite(total)?money(total,contract.currency):'Revisá los importes'}`}</p><Field id="charge-notes" label="Detalle de cargos / observaciones"><textarea id="charge-notes" className={inputClasses} rows={3} {...props('notes')}/></Field>{charge&&<TextField id="charge-reason" label="Motivo de la corrección *" minLength={5} maxLength={500} required {...props('reason')}/>}</FormShell>;
}

export function CancelMovementDialog({ resource, record, onClose, onSaved }) {
  const [reason,setReason]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const submit=async(event)=>{event.preventDefault();if(busy)return;setBusy(true);setError('');try{await financeApi.cancel(resource,record.id,reason);onSaved();}catch(failure){setError(failure.message);}finally{setBusy(false);}};
  return <FormShell title="Anular registro" intro="La operación queda conservada con su motivo de anulación. Esto corrige el registro del sistema y no revierte transferencias bancarias. Si hay operaciones dependientes, primero hay que anularlas." onClose={onClose} onSubmit={submit} busy={busy} error={error} submitLabel="Confirmar anulación"><TextField id="cancel-movement-reason" label="Motivo *" required maxLength={500} value={reason} disabled={busy} onChange={(event)=>setReason(event.target.value)}/></FormShell>;
}
