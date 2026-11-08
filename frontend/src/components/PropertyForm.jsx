import { useEffect, useState } from 'react';
import { propertyApi, personApi } from '../lib/api';
import { PROPERTY_STATUSES, personName, decimalInput } from '../lib/format';
import { FormShell, TextField } from './EntityUI';
import { Button, Field, inputClasses } from './ui';
import PersonForm from './PersonForm';
import { UtilityRulesEditor } from './UtilityRules';

const optional = ['title','property_type','unit','floor','city','province','neighborhood','postal_code','registry_number','internal_code','rooms','bedrooms','bathrooms','total_area','covered_area','condition','utility_electricity','utility_water','utility_gas','utility_municipal','utility_provincial','notes','agency_ownership_percentage'];
const numeric = ['rooms','bedrooms','bathrooms'];
const decimal = ['total_area','covered_area','agency_ownership_percentage'];
export default function PropertyForm({ property, onClose, onSaved }) {
  const [values, setValues] = useState(() => ({ ...Object.fromEntries(optional.map((key) => [key, property?.[key] ?? ''])), address: property?.address || '', price: property?.price || '', operation_type: property?.operation_type || 'alquiler', status: property?.status || 'available' }));
  const [utilityRules,setUtilityRules]=useState(property?.utility_rules || Object.entries({electricity:'utility_electricity',water:'utility_water',gas:'utility_gas',municipal:'utility_municipal',provincial:'utility_provincial'}).filter(([,key])=>property?.[key]).map(([service,key])=>({service,reference:property[key],payer:'undefined',management:'undefined',frequency:'occasional',notes:'',day:null})));
  const [owners, setOwners] = useState(property?.ownerships || []);
  const [people, setPeople] = useState([]);
  const [newOwner, setNewOwner] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [peopleError, setPeopleError] = useState('');
  useEffect(() => { const controller = new AbortController(); personApi.list(controller.signal).then(setPeople).catch((error) => { if (error.name !== 'AbortError') setPeopleError('No se pudieron cargar los propietarios. Cerrá y volvé a intentar.'); }); return () => controller.abort(); }, []);
  const props = (name) => ({ value: values[name], disabled: busy, onChange: (event) => setValues({ ...values, [name]: event.target.value }) });
  const field = (name, label, type = 'text') => <TextField key={name} id={`property-${name}`} label={label} type={type} step={type==='number'&&decimal.includes(name)?'0.01':undefined} min={type === 'number' ? 0 : undefined} {...props(name)} />;
  const submit = async (event) => {
    event.preventDefault(); if (busy) return;
    const body = { address: values.address.trim(), title: values.title.trim() || `${values.address.trim()}${values.unit ? ` · ${values.unit}` : ''}`, operation_type: values.operation_type, status: values.status, price: values.price === '' ? '0' : decimalInput(values.price) };
    if (body.price === null) { setError('Ingresá un precio válido, sin separadores de miles.'); return; }
    for (const key of optional.filter((v) => v !== 'title')) {
      const raw = String(values[key]).trim();
      if (numeric.includes(key)) body[key] = raw === '' ? null : Number(raw);
      else if (decimal.includes(key)) { body[key] = raw === '' ? null : decimalInput(raw); if (raw && body[key] === null) { setError('Revisá superficies y porcentajes: hasta dos decimales.'); return; } }
      else body[key] = raw || null;
    }
    body.utility_rules = utilityRules;
    body.ownerships = owners.map((owner) => ({ person_id: Number(owner.person_id), ownership_percentage: decimalInput(owner.ownership_percentage, 3) }));
    if (body.ownerships.some((owner) => !owner.person_id || owner.ownership_percentage === null)) { setError('Completá cada propietario y su porcentaje o quitá la fila.'); return; }
    setBusy(true); setError('');
    try { const saved = property ? await propertyApi.update(property.id, body) : await propertyApi.create(body); onSaved(saved, Boolean(property)); }
    catch (failure) { setError(failure.message); } finally { setBusy(false); }
  };
  return <><FormShell title={property ? 'Editar propiedad' : 'Nueva propiedad'} size="lg" onSubmit={submit} onClose={onClose} busy={busy} error={error || peopleError} intro="Empezá por la dirección. Podés completar propietarios, características y servicios cuando los tengas." submitLabel={property ? 'Guardar cambios' : 'Crear propiedad'}>
    <TextField id="property-address" label="Dirección *" required maxLength={200} {...props('address')} />
    <div className="grid gap-5 sm:grid-cols-3"><Field id="property-type" label="Tipo"><select id="property-type" className={inputClasses} {...props('property_type')}><option value="">Sin especificar</option>{['Departamento','Casa','Local','Oficina','Cochera','Terreno','Galpón','Otro'].map((value) => <option key={value}>{value}</option>)}</select></Field>{field('floor','Piso')}{field('unit','Departamento / unidad')}</div>
    <div className="grid gap-5 sm:grid-cols-2">{field('city','Localidad')}{field('province','Provincia')}<Field id="property-operation" label="Operación"><select id="property-operation" className={inputClasses} {...props('operation_type')}><option value="alquiler">Alquiler</option><option value="venta">Venta</option></select></Field><Field id="property-status" label="Estado"><select id="property-status" className={inputClasses} {...props('status')}>{Object.entries(PROPERTY_STATUSES).map(([value,status]) => <option key={value} value={value}>{status.label}</option>)}</select></Field></div>
    <section className="rounded-xl border border-slate-200 p-4"><div className="mb-4 flex items-center justify-between gap-2"><h3 className="text-sm font-semibold">Propietarios <span className="font-normal text-muted">· opcional</span></h3><Button type="button" variant="ghost" disabled={busy || !people.length || !!peopleError} onClick={() => setOwners([...owners, {person_id:'',ownership_percentage:owners.length ? '' : '100'}])}>Agregar</Button></div><Button type="button" variant="ghost" disabled={busy} onClick={()=>setNewOwner(true)}>+ Crear propietario sin salir</Button>{!people.length && <p className="text-xs leading-5 text-muted">Primero cargá el contacto en Propietarios. Podés guardar la propiedad sin vincularlo todavía.</p>}{owners.map((owner,index) => <div key={index} className="mb-3 grid grid-cols-[1fr_90px_auto] gap-2"><select aria-label={`Propietario ${index+1}`} className={inputClasses} disabled={busy} value={owner.person_id} onChange={(event) => setOwners(owners.map((v,i) => i===index ? {...v,person_id:event.target.value} : v))}><option value="">Seleccionar…</option>{people.map((person) => <option key={person.id} value={person.id}>{personName(person)}</option>)}</select><input aria-label="Participación porcentual" inputMode="decimal" className={inputClasses} disabled={busy} placeholder="%" value={owner.ownership_percentage} onChange={(event) => setOwners(owners.map((v,i) => i===index ? {...v,ownership_percentage:event.target.value} : v))} /><Button type="button" variant="ghost" disabled={busy} onClick={() => setOwners(owners.filter((_,i) => i!==index))}>Quitar</Button></div>)}</section>
    <details className="rounded-xl border border-slate-200 p-4"><summary className="cursor-pointer text-sm font-semibold">Características y referencia comercial <span className="font-normal text-muted">· opcional</span></summary><div className="mt-5 grid gap-5 sm:grid-cols-2">{field('title','Nombre para identificarla')}{field('internal_code','Carpeta / código interno')}{field('neighborhood','Barrio')}{field('postal_code','Código postal')}{field('registry_number','Matrícula')}{field('condition','Estado general')}{field('rooms','Ambientes','number')}{field('bedrooms','Dormitorios','number')}{field('bathrooms','Baños','number')}{field('total_area','Superficie total (m²)','number')}{field('covered_area','Superficie cubierta (m²)','number')}{field('price','Precio de referencia (ARS)')}{field('agency_ownership_percentage','Participación propia de la inmobiliaria (%)')}</div><p className="mt-3 text-xs leading-5 text-muted">La participación propia se usa para separar ingresos propios de honorarios por administrar inmuebles de terceros.</p></details>
    <UtilityRulesEditor value={utilityRules} onChange={setUtilityRules} disabled={busy} id="property-services"/>
    <p className="text-xs leading-5 text-muted">Son instrucciones de referencia. Al crear o editar el contrato, copiá y confirmá las condiciones acordadas; cada contrato conserva su configuración.</p>
    <Field id="property-notes" label="Observaciones"><textarea id="property-notes" rows={3} className={inputClasses} {...props('notes')} /></Field>
  </FormShell>{newOwner&&<PersonForm mode="owners" onClose={()=>setNewOwner(false)} onSaved={(person)=>{setPeople([...people,person]);setOwners([...owners,{person_id:person.id,ownership_percentage:owners.length?'':'100'}]);setNewOwner(false);}}/>}</>;
}
