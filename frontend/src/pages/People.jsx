import DeadlineBar from '../components/DeadlineBar';
import { useCallback, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Eye, Pencil, Plus, ShieldCheck } from 'lucide-react';
import { personApi, propertyApi, ownerApi, contractApi } from '../lib/api';
import { contractTenantIds, dateLabel, personName, normalizeSearch } from '../lib/format';
import useApiData from '../hooks/useApiData';
import { Alert, Button, Card, EmptyState, Loading, PageHeading } from '../components/ui';
import { DetailFields, RetryError, SearchInput } from '../components/EntityUI';
import Dialog from '../components/Dialog';
import PersonForm from '../components/PersonForm';
import { propertyLabel } from '../components/RentalDialogs';

export default function People({ mode }) {
  const owners=mode==='owners';
  const location=useLocation();
  const [search,setSearch]=useState(''),[scope,setScope]=useState('all'),[form,setForm]=useState(null),[detailId,setDetailId]=useState(()=>Number(new URLSearchParams(location.search).get('ficha'))||null),[notice,setNotice]=useState('');
  const loader=useCallback(async(signal)=>{const [people,properties,ownerships,contracts]=await Promise.all([personApi.list(signal),propertyApi.list(signal),ownerApi.list(signal),contractApi.list(signal)]);return{people,properties,ownerships,contracts};},[]);
  const {data,loading,error,reload}=useApiData(loader);
  const ownerLinks=(id)=>data?.ownerships.filter((link)=>link.person_id===id)||[];
  const tenantLinks=(id)=>data?.contracts.filter((c)=>contractTenantIds(c).includes(id))||[];
  const deadlines=useMemo(()=>{
    const result=new Map(),latest=new Map();
    for(const contract of data?.contracts||[]){
      if(!['active','expired'].includes(contract.status))continue;
      const key=contract.property_id;
      if(!latest.has(key)||contract.start_date>latest.get(key).start_date)latest.set(key,contract);
    }
    const propertyOwners=new Map();
    for(const link of data?.ownerships||[]){if(!propertyOwners.has(link.property_id))propertyOwners.set(link.property_id,[]);propertyOwners.get(link.property_id).push(link.person_id);}
    for(const contract of latest.values())for(const id of owners?(propertyOwners.get(contract.property_id)||[]):contractTenantIds(contract)){
      if(!result.has(id)||contract.end_date<result.get(id).end_date)result.set(id,contract);
    }
    return result;
  },[data,owners]);
  const expiringContract=id=>deadlines.get(id);
  const guarantees=(id)=>data?.contracts.filter((c)=>c.guarantor_ids?.includes(id))||[];
  const filtered=useMemo(()=>data?.people.filter((p)=>{const linked=owners?ownerLinks(p.id).length:tenantLinks(p.id).length;return(scope==='all'||scope==='linked'&&linked||scope==='guarantor'&&guarantees(p.id).length||scope==='available'&&!linked)&&normalizeSearch(`${personName(p)} ${p.dni||''} ${p.cuit_cuil||''} ${p.phone||''} ${p.email||''}`).includes(normalizeSearch(search));}).sort((a,b)=>personName(a).localeCompare(personName(b),'es'))||[],[data,owners,search,scope]);
  const selected=data?.people.find((p)=>p.id===detailId);
  const saved=(person)=>{setForm(null);setDetailId(person.id);setNotice('Los datos se guardaron correctamente.');reload();};
  return <><PageHeading eyebrow="Personas y vínculos" title={owners?'Propietarios':'Inquilinos y garantes'} description={owners?'Contactos, participaciones y datos para liquidaciones y transferencias.':'Una ficha por persona, con sus contratos, contactos y garantías.'}><Button disabled={loading||!!error} onClick={()=>setForm({person:null})}><Plus size={17}/>{owners?'Nuevo propietario':'Nueva persona'}</Button></PageHeading>{notice&&<div className="mb-5"><Alert type="success" onDismiss={()=>setNotice('')}>{notice}</Alert></div>}<Card className="overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 p-5"><div className="flex flex-wrap gap-1 rounded-xl bg-slate-50 p-1">{[['all','Todos'],['linked',owners?'Con propiedades':'Con contratos'],...(!owners?[['guarantor','Garantes']]:[]),['available','Sin vínculo']].map(([value,label])=><button key={value} className={`rounded-lg px-3 py-2 text-xs font-medium ${scope===value?'bg-white text-ink shadow-xs':'text-muted'}`} onClick={()=>setScope(value)}>{label}</button>)}</div><div className="w-full sm:w-80"><SearchInput id="people-search" value={search} onChange={setSearch} placeholder="Nombre, DNI, teléfono o mail…"/></div></div>{loading?<Loading/>:error?<div className="p-5"><RetryError error={error} onRetry={reload}/></div>:!filtered.length?<EmptyState title="No hay personas para mostrar" description="Completá nombre y apellido para comenzar; contacto y datos bancarios son opcionales."/>:<div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-[10px] tracking-widest text-muted uppercase"><tr><th className="px-5 py-4">Persona</th><th className="px-5 py-4">Contacto</th><th className="px-5 py-4">Vínculos</th><th className="px-5 py-4">Vencimiento de contrato</th><th className="px-5 py-4 text-right">Acciones</th></tr></thead><tbody className="divide-y divide-slate-100">{filtered.map((p)=><tr key={p.id} className="hover:bg-slate-50/60"><td className="px-5 py-5"><button className="text-left font-semibold hover:text-brand" onClick={()=>setDetailId(p.id)}>{personName(p)}</button><p className="mt-1 text-xs text-muted">{p.dni?`DNI ${p.dni}`:'DNI sin cargar'}</p></td><td className="px-5 py-5"><p className="text-xs">{p.phone||'Sin teléfono'}</p><p className="mt-1 text-xs text-muted">{p.email||'Sin correo'}</p></td><td className="px-5 py-5"><div className="flex flex-wrap gap-1 text-xs">{!!ownerLinks(p.id).length&&<span className="rounded-full bg-emerald-50 px-2.5 py-1 text-brand">{ownerLinks(p.id).length} propiedades</span>}{!!tenantLinks(p.id).length&&<span className="rounded-full bg-slate-100 px-2.5 py-1 text-muted">{tenantLinks(p.id).length} contratos</span>}{!!guarantees(p.id).length&&<span className="rounded-full bg-amber-50 px-2.5 py-1 text-amber-800">Garante</span>}</div></td><td className="min-w-64 px-5 py-5">{expiringContract(p.id)?<DeadlineBar dueDate={expiringContract(p.id).end_date} label="Contrato más próximo" kind="contract"/>:<span className="text-xs text-muted">Sin contrato activo</span>}</td><td className="px-5 py-5"><div className="flex justify-end"><Button variant="ghost" aria-label={`Ver ${personName(p)}`} onClick={()=>setDetailId(p.id)}><Eye size={16}/></Button><Button variant="ghost" aria-label={`Editar ${personName(p)}`} onClick={()=>setForm({person:p})}><Pencil size={16}/></Button></div></td></tr>)}</tbody></table></div>}</Card>
    {selected&&<Dialog title={personName(selected)} size="lg" onClose={()=>setDetailId(null)}><div className="space-y-5 p-6"><DetailFields title="Datos de contacto" fields={[["DNI",selected.dni],["CUIT / CUIL",selected.cuit_cuil],["Teléfono",selected.phone],["Email",selected.email],["Domicilio",selected.address],["Ocupación",selected.occupation],["Empleador",selected.employer],["Teléfono laboral",selected.work_phone]]}/><DetailFields title="Datos bancarios" fields={[["Alias",selected.bank_alias],["CBU",selected.cbu],["Banco",selected.bank_name],["Titular",selected.bank_holder]]}/>{!!ownerLinks(selected.id).length&&<DetailFields title="Propiedades y participación" fields={ownerLinks(selected.id).map((link)=>[propertyLabel(data.properties.find((p)=>p.id===link.property_id)),`${link.ownership_percentage}%`])}/>}<section className="rounded-xl border border-slate-200 p-5"><h3 className="text-sm font-semibold">Contratos y garantías</h3>{!tenantLinks(selected.id).length&&!guarantees(selected.id).length?<p className="mt-3 text-sm text-muted">Sin contratos asociados. Seleccioná esta persona como inquilino o garante al crear un alquiler.</p>:[...tenantLinks(selected.id),...guarantees(selected.id)].map((c)=><Link key={c.id} to={`/contratos?ficha=${c.id}`} className="mt-3 block rounded-lg bg-slate-50 p-3 text-sm hover:text-brand"><p className="font-medium">{propertyLabel(data.properties.find((p)=>p.id===c.property_id))}</p><p className="mt-1 text-xs text-muted">{dateLabel(c.start_date)} — {dateLabel(c.end_date)} · {c.guarantor_ids?.includes(selected.id)?'Garante':'Inquilino'}</p></Link>)}</section>{selected.notes&&<p className="whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-sm text-muted">{selected.notes}</p>}<div className="flex justify-end"><Button onClick={()=>setForm({person:selected})}>Editar datos</Button></div></div></Dialog>}
    {form&&<PersonForm person={form.person} mode={scope==='guarantor'?'guarantors':mode} onClose={()=>setForm(null)} onSaved={saved}/>}
  </>;
}
