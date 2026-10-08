import { useCallback, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Plus, Pencil, ArrowUpRight, FileText } from 'lucide-react';
import { contractApi, personApi, propertyApi } from '../lib/api';
import { contractTenantIds, personName, normalizeSearch, money, dateLabel, CONTRACT_STATUSES } from '../lib/format';
import useApiData from '../hooks/useApiData';
import { Alert, Button, Card, EmptyState, Loading, PageHeading, inputClasses } from '../components/ui';
import { RetryError, SearchInput, StatusBadge } from '../components/EntityUI';
import ContractForm from '../components/ContractForm';

export default function Contracts() {
  const location = useLocation();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [form, setForm] = useState(location.state?.createForTenant ? { contract: null, tenantId: location.state.createForTenant } : null);
  const [notice, setNotice] = useState('');
  const loader = useCallback(async (signal) => {
    const [contracts, people, properties] = await Promise.all([contractApi.list(signal), personApi.list(signal), propertyApi.list(signal)]);
    return { contracts, people, properties };
  }, []);
  const { data, loading, error, reload } = useApiData(loader);
  const propertyFor = (contract) => data.properties.find((property) => property.id === contract.property_id);
  const tenantsFor = (contract) => contractTenantIds(contract).map((id) => personName(data.people.find((person) => person.id === id)));
  const filtered = useMemo(() => !data ? [] : data.contracts.filter((contract) => {
    const property = data.properties.find((item) => item.id === contract.property_id);
    const tenants = contractTenantIds(contract).map((id) => personName(data.people.find((person) => person.id === id))).join(' ');
    return (!status || contract.status === status) && normalizeSearch(`${property?.title || ''} ${property?.address || ''} ${tenants}`).includes(normalizeSearch(search.trim()));
  }).sort((a, b) => b.id - a.id), [data, search, status]);
  const saved = (contract, editing) => {
    setForm(null);
    if (!editing) { navigate(`/contratos/${contract.id}`, { state: { notice: 'El contrato se creó correctamente.' } }); return; }
    setNotice('El contrato se actualizó correctamente.'); reload();
  };
  return <><PageHeading eyebrow="Gestión de alquileres" title="Contratos" description="Propiedades, inquilinos y condiciones de cada alquiler."><Button disabled={loading || Boolean(error)} onClick={() => setForm({ contract: null })}><Plus size={17} />Nuevo contrato</Button></PageHeading>{notice && <div className="mb-5"><Alert type="success" onDismiss={() => setNotice('')}>{notice}</Alert></div>}{error && <div className="mb-5"><RetryError error={error} onRetry={reload} /></div>}<Card className="overflow-hidden"><div className="flex flex-col justify-between gap-3 border-b border-slate-100 p-5 sm:flex-row"><div className="sm:w-96"><SearchInput id="contract-search" value={search} onChange={setSearch} placeholder="Buscar propiedad o inquilino…" /></div><label className="sr-only" htmlFor="contract-filter-status">Estado del contrato</label><select id="contract-filter-status" value={status} onChange={(event) => setStatus(event.target.value)} className={`${inputClasses} sm:w-48`}><option value="">Todos los estados</option>{Object.entries(CONTRACT_STATUSES).map(([value, definition]) => <option key={value} value={value}>{definition.label}</option>)}</select></div>{loading ? <Loading label="Cargando contratos…" /> : error ? <EmptyState title="El listado no está disponible" description="Reintentá para consultar tus contratos." /> : !filtered.length ? <EmptyState icon={FileText} title={search || status ? 'No encontramos coincidencias' : 'Todavía no hay contratos'} description={search || status ? 'Probá otra búsqueda o cambiá el filtro de estado.' : 'Creá un contrato seleccionando una propiedad y sus inquilinos.'}>{(search || status) && <Button variant="secondary" onClick={() => { setSearch(''); setStatus(''); }}>Limpiar filtros</Button>}</EmptyState> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">Listado de contratos de alquiler</caption><thead className="bg-slate-50/70 text-[10px] tracking-widest text-muted uppercase"><tr><th scope="col" className="px-5 py-4">Propiedad e inquilinos</th><th scope="col" className="hidden px-5 py-4 lg:table-cell">Vigencia</th><th scope="col" className="px-5 py-4 text-right">Alquiler vigente</th><th scope="col" className="px-5 py-4">Estado</th><th scope="col" className="px-5 py-4"><span className="sr-only">Acciones</span></th></tr></thead><tbody className="divide-y divide-slate-100">{filtered.map((contract) => <tr key={contract.id} className="hover:bg-slate-50/60"><td className="px-5 py-5"><Link to={`/contratos/${contract.id}`} className="font-semibold hover:text-brand hover:underline">{propertyFor(contract)?.title || 'Propiedad no disponible'}</Link><p className="mt-1 max-w-72 text-xs leading-5 text-muted">{tenantsFor(contract).join(' · ')}</p></td><td className="hidden whitespace-nowrap px-5 py-5 text-xs text-muted lg:table-cell">{dateLabel(contract.start_date)}<br /><span className="mt-1 inline-block">hasta {dateLabel(contract.end_date)}</span></td><td className="whitespace-nowrap px-5 py-5 text-right"><p className="font-semibold tabular-nums">{money(contract.current_rent, contract.currency)}</p><p className="mt-1 text-xs text-muted">{contract.currency}</p></td><td className="px-5 py-5"><StatusBadge value={contract.status} definitions={CONTRACT_STATUSES} /></td><td className="px-5 py-5"><div className="flex justify-end gap-2"><button onClick={() => setForm({ contract })} aria-label={`Editar contrato de ${propertyFor(contract)?.title || 'la propiedad'}`} className="rounded-lg border border-slate-200 p-2 text-muted hover:text-brand"><Pencil size={15} /></button><Link to={`/contratos/${contract.id}`} aria-label="Ver detalle del contrato" className="rounded-lg border border-slate-200 p-2 text-muted hover:text-brand"><ArrowUpRight size={16} /></Link></div></td></tr>)}</tbody></table><p className="border-t border-slate-100 px-5 py-4 text-xs text-muted">{filtered.length} {filtered.length === 1 ? 'contrato' : 'contratos'}</p></div>}</Card>{form && data && !loading && !error && <ContractForm key={form.contract?.id || 'new'} contract={form.contract} preselectedTenant={form.tenantId} people={data.people} properties={data.properties} contracts={data.contracts} onClose={() => setForm(null)} onSaved={saved} />}</>;
}
