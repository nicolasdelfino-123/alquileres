import { useEffect, useMemo, useState } from 'react';
import { contractApi, chargeApi } from '../lib/api';
import { personName, normalizeSearch, contractTenantIds, decimalInput, CONTRACT_STATUSES } from '../lib/format';
import { FormShell, SearchInput, TextField } from './EntityUI';
import { Button, Field, inputClasses, Loading } from './ui';
import PersonForm from './PersonForm';
import { UtilityRulesEditor } from './UtilityRules';

const indices = ['ICL', 'IPC', 'RIPTE'];
export default function ContractForm({ contract, people: initialPeople, properties, contracts, preselectedTenant, onClose, onSaved }) {
  const editing = Boolean(contract);
  const [utilityRules,setUtilityRules]=useState(contract?.utility_rules || []);
  const [people, setPeople] = useState(initialPeople);
  const [newPerson, setNewPerson] = useState(null);
  const [values, setValues] = useState(() => ({
    property_id: String(contract?.property_id || ''),
    tenant_ids: contract ? contractTenantIds(contract) : preselectedTenant && people.some((person) => person.id === Number(preselectedTenant)) ? [Number(preselectedTenant)] : [],
    tenant_id: contract?.tenant_id || Number(preselectedTenant) || '',
    start_date: contract?.start_date || '', end_date: contract?.end_date || '',
    initial_rent: contract?.initial_rent || '', current_rent: contract?.current_rent || '',
    currency: contract?.currency || 'ARS', adjustment_frequency_months: contract?.adjustment_frequency_months?.toString() || '',
    adjustment_index: contract?.adjustment_index || '', administration_percentage: contract?.administration_percentage ?? '',
    collection_alias: contract?.collection_alias || '', collection_cbu: contract?.collection_cbu || '',
    guarantor_ids: contract?.guarantor_ids || [], payment_day: contract?.payment_day || '10', payment_method: contract?.payment_method || '', deposit_amount: contract?.deposit_amount || '', signed_date: contract?.signed_date || '', next_adjustment_date: contract?.next_adjustment_date || '', fixed_adjustment_percentage: contract?.fixed_adjustment_percentage || '',
    status: contract?.status || 'active', notes: contract?.notes || '',
  }));
  const [indexMode, setIndexMode] = useState(contract?.adjustment_index ? indices.includes(contract.adjustment_index) ? contract.adjustment_index : 'other' : '');
  const [tenantSearch, setTenantSearch] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [checkError, setCheckError] = useState('');
  const [checking, setChecking] = useState(editing);
  const [checked, setChecked] = useState(!editing);
  const [locked, setLocked] = useState(false);
  const [checkVersion, setCheckVersion] = useState(0);
  useEffect(() => {
    if (!contract) return;
    const controller = new AbortController();
    setChecking(true); setChecked(false); setCheckError('');
    chargeApi.list(contract.id, controller.signal).then((charges) => {
      if (!controller.signal.aborted) { setLocked(charges.length > 0); setChecked(true); }
    }).catch((failure) => { if (!controller.signal.aborted) setCheckError(failure.message); })
      .finally(() => { if (!controller.signal.aborted) setChecking(false); });
    return () => controller.abort();
  }, [contract?.id, checkVersion]);
  const frozen = locked || !checked || busy;
  const change = (event) => {
    const { name, value } = event.target;
    setValues((current) => ({ ...current, [name]: value, ...(name === 'initial_rent' && !editing && current.current_rent === current.initial_rent ? { current_rent: value } : {}) }));
  };
  const props = (name, disabled = busy) => ({ name, value: values[name], onChange: change, disabled });
  const visiblePeople = useMemo(() => people.filter((person) => normalizeSearch(`${personName(person)} ${person.dni || ''}`).includes(normalizeSearch(tenantSearch.trim()))).sort((a, b) => personName(a).localeCompare(personName(b), 'es')), [people, tenantSearch]);
  const selectTenant = (identifier) => {
    setValues((current) => {
      const tenant_ids = current.tenant_ids.includes(identifier) ? current.tenant_ids.filter((id) => id !== identifier) : [...current.tenant_ids, identifier];
      return { ...current, tenant_ids, tenant_id: tenant_ids.includes(Number(current.tenant_id)) ? current.tenant_id : tenant_ids[0] || '' };
    });
  };
  const currencies = [...new Set(['ARS', 'USD', 'EUR', ...contracts.map((item) => item.currency).filter(Boolean), values.currency])];
  const submit = async (event) => {
    event.preventDefault();
    if (busy || !checked) return;
    if (!properties.some((property) => property.id === Number(values.property_id))) { setError('Seleccioná una propiedad.'); return; }
    if (!values.tenant_ids.length || !values.tenant_ids.every((id) => people.some((person) => person.id === id))) { setError('Seleccioná al menos un inquilino disponible.'); return; }
    if (!values.tenant_ids.includes(Number(values.tenant_id))) { setError('Seleccioná un inquilino principal entre los elegidos.'); return; }
    if (!values.start_date || !values.end_date || values.end_date <= values.start_date) { setError('La fecha de finalización debe ser posterior al inicio.'); return; }
    const initial = decimalInput(values.initial_rent), current = decimalInput(values.current_rent);
    if (initial === null || current === null) { setError('Los importes deben ser positivos o cero, sin separadores de miles y con hasta dos decimales.'); return; }
    const administration = values.administration_percentage === '' ? null : decimalInput(values.administration_percentage, 3);
    if (values.administration_percentage !== '' && (administration === null || Number(administration) > 100)) { setError('El porcentaje de administración debe estar entre 0 y 100.'); return; }
    const frequency = values.adjustment_frequency_months === '' ? null : Number(values.adjustment_frequency_months);
    if (frequency !== null && (!Number.isInteger(frequency) || frequency <= 0 || frequency > 2147483647)) { setError('La frecuencia de ajustes debe ser una cantidad positiva de meses.'); return; }
    const changesPeriod = !contract || Number(values.property_id) !== contract.property_id || values.start_date !== contract.start_date || values.end_date !== contract.end_date || values.status !== contract.status;
    if (changesPeriod && values.status === 'active' && contracts.some((item) => item.id !== contract?.id && item.property_id === Number(values.property_id) && item.status === 'active' && item.start_date <= values.end_date && item.end_date >= values.start_date)) { setError('Esta propiedad ya tiene un contrato activo que se superpone con esas fechas.'); return; }
    const body = {
      utility_rules: utilityRules,
      collection_alias: values.collection_alias.trim() || null, collection_cbu: values.collection_cbu.trim() || null,
    guarantor_ids: values.guarantor_ids, payment_day: Number(values.payment_day), payment_method: values.payment_method || null,
      deposit_amount: values.deposit_amount === '' ? null : decimalInput(values.deposit_amount), signed_date: values.signed_date || null,
      next_adjustment_date: values.next_adjustment_date || null, fixed_adjustment_percentage: values.fixed_adjustment_percentage === '' ? null : decimalInput(values.fixed_adjustment_percentage),
      property_id: Number(values.property_id), tenant_ids: values.tenant_ids, tenant_id: Number(values.tenant_id),
      start_date: values.start_date, end_date: values.end_date, initial_rent: initial, current_rent: current,
      currency: values.currency, adjustment_frequency_months: frequency, adjustment_index: values.adjustment_index.trim() || null,
      administration_percentage: administration, status: values.status, notes: values.notes.trim() || null,
    };
    setBusy(true); setError('');
    try {
      const saved = editing ? await contractApi.update(contract.id, body) : await contractApi.create(body);
      onSaved(saved, editing);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  return <><FormShell title={editing ? 'Editar contrato' : 'Nuevo contrato'} size="lg" intro={locked ? 'Este contrato tiene mensualidades: la propiedad, los inquilinos, las fechas y la moneda se conservan para proteger su historial.' : 'Seleccioná una propiedad y uno o varios inquilinos. Los importes se guardan sin modificar mensualidades anteriores.'} busy={busy} error={error || checkError} onClose={onClose} onSubmit={submit} submitDisabled={!checked} submitLabel={editing ? 'Guardar cambios' : 'Crear contrato'}>{checking && <Loading label="Consultando mensualidades del contrato…" />}{checkError && <Button type="button" variant="secondary" onClick={() => setCheckVersion((value) => value + 1)}>Reintentar verificación</Button>}<Field id="contract-property" label="Propiedad"><select id="contract-property" required className={inputClasses} {...props('property_id', frozen)}><option value="">Seleccioná una propiedad</option>{properties.map((property) => <option key={property.id} value={property.id}>{property.title} · {property.address}</option>)}</select>{!properties.length && <p className="mt-2 text-xs text-muted">Primero incorporá una propiedad desde la sección Propiedades.</p>}</Field><div className="flex justify-end"><Button type="button" variant="ghost" disabled={frozen} onClick={()=>setNewPerson('tenants')}>+ Crear inquilino sin salir</Button></div><fieldset className="rounded-xl border border-slate-200 p-4"><legend className="px-1 text-sm font-medium">Inquilinos · {values.tenant_ids.length} seleccionados</legend><SearchInput id="contract-tenant-search" value={tenantSearch} onChange={setTenantSearch} placeholder="Buscar personas por nombre o DNI…" /><div className="mt-3 max-h-44 space-y-1 overflow-y-auto">{visiblePeople.map((person) => <label key={person.id} className={`flex items-center gap-3 rounded-lg px-2 py-2 text-sm ${values.tenant_ids.includes(person.id) ? 'bg-emerald-50' : 'hover:bg-slate-50'}`}><input type="checkbox" checked={values.tenant_ids.includes(person.id)} onChange={() => selectTenant(person.id)} disabled={frozen} className="size-4 shrink-0 accent-brand" /><span className="flex-1">{personName(person)}{person.dni && <span className="ml-2 text-xs text-muted">DNI {person.dni}</span>}</span></label>)}{!visiblePeople.length && <p className="py-3 text-xs text-muted">{people.length ? 'No hay personas que coincidan con la búsqueda.' : 'Primero agregá un contacto desde Inquilinos.'}</p>}</div>{values.tenant_ids.length > 0 && <div className="mt-4"><Field id="contract-primary" label="Inquilino principal"><select id="contract-primary" className={inputClasses} required {...props('tenant_id', frozen)}>{values.tenant_ids.map((id) => <option key={id} value={id}>{personName(people.find((person) => person.id === id))}</option>)}</select></Field></div>}</fieldset><div className="grid gap-5 sm:grid-cols-2"><TextField id="contract-start" label="Fecha de inicio" type="date" required {...props('start_date', frozen)} /><TextField id="contract-end" label="Fecha de finalización" type="date" required {...props('end_date', frozen)} /><TextField id="contract-initial" label="Alquiler inicial" inputMode="decimal" required hint="Hasta dos decimales, sin separadores de miles." {...props('initial_rent')} /><TextField id="contract-current" label="Alquiler vigente" inputMode="decimal" required hint="Se aplica a nuevas mensualidades, sin recalcular las existentes." {...props('current_rent')} /><Field id="contract-currency" label="Moneda"><select id="contract-currency" className={inputClasses} {...props('currency', frozen)}>{currencies.map((currency) => <option key={currency} value={currency}>{currency}</option>)}</select></Field><TextField id="contract-frequency" label="Ajustes cada (meses)" type="number" min={1} step={1} max={2147483647} hint="Opcional. Dejá vacío si no hay frecuencia definida." {...props('adjustment_frequency_months')} /><Field id="contract-index" label="Índice de ajuste"><select id="contract-index" value={indexMode} disabled={busy} className={inputClasses} onChange={(event) => { const mode = event.target.value; setIndexMode(mode); setValues((current) => ({ ...current, adjustment_index: mode === 'other' ? '' : mode })); }}><option value="">Sin índice definido</option>{indices.map((index) => <option key={index} value={index}>{index}</option>)}<option value="other">Otro índice</option></select></Field><TextField id="contract-admin" label="Administración (%)" inputMode="decimal" hint="Opcional, entre 0 y 100." {...props('administration_percentage')} />{indexMode === 'other' && <TextField id="contract-custom-index" label="Nombre del índice" maxLength={50} required {...props('adjustment_index')} />}<Field id="contract-status" label="Estado"><select id="contract-status" className={inputClasses} {...props('status')}>{Object.entries(CONTRACT_STATUSES).map(([value, status]) => <option key={value} value={value}>{status.label}</option>)}</select></Field></div><details open={values.guarantor_ids.length > 0} className="rounded-xl border border-slate-200 p-4"><summary className="cursor-pointer text-sm font-semibold">Garantes · opcional</summary><p className="mt-3 text-xs leading-5 text-muted">Seleccioná contactos existentes. Podés cargar sus datos desde Personas / Inquilinos antes de asociarlos al contrato.</p><Button type="button" variant="ghost" disabled={frozen} onClick={()=>setNewPerson('guarantors')}>+ Crear garante</Button><div className="mt-3 max-h-40 overflow-y-auto">{people.filter((person) => !values.tenant_ids.includes(person.id)).map((person) => <label key={person.id} className="flex items-center gap-3 py-2 text-sm"><input type="checkbox" disabled={frozen} checked={values.guarantor_ids.includes(person.id)} onChange={() => setValues({...values,guarantor_ids:values.guarantor_ids.includes(person.id) ? values.guarantor_ids.filter((id) => id!==person.id) : [...values.guarantor_ids,person.id]})} />{personName(person)} <span className="text-xs text-muted">{person.phone}</span></label>)}</div></details><div className="grid gap-5 sm:grid-cols-2"><TextField id="contract-payment-day" label="Día de vencimiento mensual" type="number" min={1} max={31} required {...props('payment_day')} /><Field id="contract-payment-method" label="Medio de pago habitual"><select id="contract-payment-method" className={inputClasses} {...props('payment_method')}><option value="">Sin definir</option><option value="transfer">Transferencia</option><option value="cash">Efectivo</option><option value="other">Otro</option></select></Field><TextField id="contract-next-adjustment" label="Próximo aumento (opcional)" type="date" {...props('next_adjustment_date')} /><TextField id="contract-fixed-percentage" label="Aumento pactado (%) · opcional" inputMode="decimal" {...props('fixed_adjustment_percentage')} /></div><details className="rounded-xl border border-slate-200 p-4"><summary className="cursor-pointer text-sm font-semibold">Depósito y firma · opcionales</summary><div className="mt-4 grid gap-5 sm:grid-cols-2"><TextField id="contract-deposit" label="Depósito de garantía" inputMode="decimal" {...props('deposit_amount')} /><TextField id="contract-signed-date" label="Fecha de firma" type="date" {...props('signed_date')} /></div></details><details className="rounded-xl border border-slate-200 p-4"><summary className="cursor-pointer text-sm font-semibold">Cuenta para cobrar el alquiler · opcional</summary><p className="mt-3 text-xs leading-5 text-muted">Es la cuenta que se indicará al inquilino. La cuenta del propietario para recibir transferencias se carga en su ficha.</p><div className="mt-4 grid gap-4 sm:grid-cols-2"><TextField id="contract-collection-alias" label="Alias de cobro" maxLength={100} {...props('collection_alias')} /><TextField id="contract-collection-cbu" label="CBU de cobro" maxLength={22} {...props('collection_cbu')} /></div></details><Field id="contract-notes" label="Notas"><textarea id="contract-notes" rows={3} className={`${inputClasses} resize-y`} {...props('notes')} /></Field><UtilityRulesEditor value={utilityRules} onChange={setUtilityRules} disabled={busy} id="contract-services"/><Button type="button" variant="secondary" disabled={busy||utilityRules.length>0||!properties.find(p=>p.id===Number(values.property_id))?.utility_rules?.length} onClick={()=>setUtilityRules(properties.find(p=>p.id===Number(values.property_id))?.utility_rules?.map(rule=>({...rule}))||[])}>Copiar condiciones de servicios de la propiedad</Button><p className="text-xs leading-5 text-muted">Confirmá las condiciones del contrato. Los cambios en la propiedad no modifican lo acordado aquí. Para reemplazar una configuración, quitá primero sus conceptos.</p></FormShell>{newPerson&&<PersonForm mode={newPerson} onClose={()=>setNewPerson(null)} onSaved={(person)=>{setPeople([...people,person]);setValues((current)=>newPerson==='guarantors'?{...current,guarantor_ids:[...current.guarantor_ids,person.id]}:{...current,tenant_ids:[...current.tenant_ids,person.id],tenant_id:current.tenant_id||person.id});setNewPerson(null);}}/>}</>;
}
