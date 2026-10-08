import { useEffect, useMemo, useState } from 'react';
import { Building2, Plus, Search, SlidersHorizontal, Pencil, MapPin, ArrowUpRight, RefreshCw, KeyRound, CheckCircle2 } from 'lucide-react';
import { propertyApi } from '../lib/api';
import { money, PROPERTY_STATUSES } from '../lib/format';
import { Alert, Button, Card, EmptyState, Loading, PageHeading, inputClasses } from '../components/ui';
import PropertyForm from '../components/PropertyForm';

function StatusBadge({ status }) {
  const definition = PROPERTY_STATUSES[status] || { label: status, classes: 'bg-slate-100 text-slate-600 ring-slate-600/10' };
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 ring-inset ${definition.classes}`}><span className="size-1.5 rounded-full bg-current" />{definition.label}</span>;
}
const normalize = (text) => String(text).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

export default function Properties() {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');
  const [operation, setOperation] = useState('');
  const [status, setStatus] = useState('');
  const [retry, setRetry] = useState(0);
  const [form, setForm] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    propertyApi.list(controller.signal).then((data) => {
      if (!Array.isArray(data)) throw new Error('No pudimos leer el listado de propiedades.');
      setProperties(data); setLoaded(true);
    }).catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [retry]);
  const filtered = useMemo(() => properties.filter((property) => {
    const query = normalize(search.trim());
    return (!query || normalize(`${property.title} ${property.address} ${property.id}`).includes(query)) && (!operation || property.operation_type === operation) && (!status || property.status === status);
  }).sort((a, b) => b.id - a.id), [properties, search, operation, status]);
  const save = (property, editing) => {
    setProperties((current) => editing ? current.map((item) => item.id === property.id ? property : item) : [property, ...current]);
    setNotice(editing ? 'Los cambios se guardaron correctamente.' : 'La propiedad se incorporó a tu cartera.');
    setForm(null);
  };
  const clearFilters = () => { setSearch(''); setOperation(''); setStatus(''); };
  const hasFilters = Boolean(search || operation || status);
  const summaries = [
    { label: 'Total de propiedades', value: properties.length, icon: Building2, color: 'bg-slate-100 text-slate-600' },
    { label: 'Disponibles', value: properties.filter((property) => property.status === 'available').length, icon: CheckCircle2, color: 'bg-emerald-50 text-brand' },
    { label: 'En alquiler', value: properties.filter((property) => property.operation_type === 'alquiler').length, icon: KeyRound, color: 'bg-blue-50 text-blue-700' },
  ];
  return <><PageHeading eyebrow="Tu cartera inmobiliaria" title="Propiedades" description="Toda la información de tus inmuebles, en un solo lugar."><Button onClick={() => setForm({ property: null })}><Plus size={18} />Nueva propiedad</Button></PageHeading>{notice && <div className="mb-5"><Alert type="success" onDismiss={() => setNotice('')}>{notice}</Alert></div>}{error && <div className="mb-5"><Alert><div className="flex flex-wrap items-center justify-between gap-3"><span>{error}</span><button className="inline-flex items-center gap-2 font-semibold underline underline-offset-4" onClick={() => setRetry((value) => value + 1)} disabled={loading}><RefreshCw size={14} />Reintentar</button></div></Alert></div>}<div className="mb-6 grid gap-4 sm:grid-cols-3">{summaries.map(({ label, value, icon: Icon, color }) => <Card key={label} className="flex items-center gap-4 p-5"><span className={`flex size-12 shrink-0 items-center justify-center rounded-xl ${color}`}><Icon size={22} strokeWidth={1.6} /></span><div><p className="text-xs text-muted">{label}</p><p className="mt-1 text-2xl font-semibold tracking-tight">{loaded ? value : '—'}</p></div></Card>)}</div><Card className="overflow-hidden"><div className="flex flex-col gap-4 border-b border-slate-100 p-5 lg:flex-row lg:items-center lg:justify-between"><div className="relative lg:w-80"><label className="sr-only" htmlFor="property-search">Buscar propiedades</label><Search size={18} className="absolute top-1/2 left-3.5 -translate-y-1/2 text-slate-400" /><input id="property-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por nombre o dirección…" className={`${inputClasses} py-2.5 pl-10`} /></div><div className="flex flex-wrap items-center gap-2"><SlidersHorizontal size={16} className="mr-1 hidden text-slate-400 sm:block" /><label className="sr-only" htmlFor="filter-operation">Filtrar por operación</label><select id="filter-operation" value={operation} onChange={(event) => setOperation(event.target.value)} className={`${inputClasses} w-auto flex-1 py-2.5 sm:flex-none`}><option value="">Todas las operaciones</option><option value="alquiler">Alquiler</option><option value="venta">Venta</option></select><label className="sr-only" htmlFor="filter-status">Filtrar por estado</label><select id="filter-status" value={status} onChange={(event) => setStatus(event.target.value)} className={`${inputClasses} w-auto flex-1 py-2.5 sm:flex-none`}><option value="">Todos los estados</option>{Object.entries(PROPERTY_STATUSES).map(([value, definition]) => <option key={value} value={value}>{definition.label}</option>)}</select></div></div>{loading ? <Loading label="Cargando propiedades…" /> : !loaded ? <EmptyState title="El listado no está disponible" description="Reintentá la conexión para consultar tus propiedades." /> : filtered.length === 0 ? <EmptyState icon={hasFilters ? Search : Building2} title={hasFilters ? 'No encontramos coincidencias' : 'Tu próxima propiedad empieza acá'} description={hasFilters ? 'Probá con otra búsqueda o ajustá los filtros.' : 'Incorporá tu primer inmueble para empezar a organizar tu cartera.'}>{hasFilters ? <Button variant="secondary" onClick={clearFilters}>Limpiar filtros</Button> : <Button onClick={() => setForm({ property: null })}><Plus size={17} />Crear propiedad</Button>}</EmptyState> : <><div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">Listado de propiedades de Pako</caption><thead><tr className="border-b border-slate-100 bg-slate-50/70 text-[10px] font-semibold tracking-[0.1em] text-muted uppercase"><th scope="col" className="px-5 py-4">Propiedad</th><th scope="col" className="hidden px-5 py-4 md:table-cell">Operación</th><th scope="col" className="px-5 py-4 text-right">Precio · ARS</th><th scope="col" className="hidden px-5 py-4 lg:table-cell">Estado</th><th scope="col" className="px-5 py-4 text-right"><span className="sr-only">Acciones</span></th></tr></thead><tbody className="divide-y divide-slate-100">{filtered.map((property) => <tr key={property.id} className="transition-colors hover:bg-slate-50/70"><td className="px-5 py-5"><div className="flex items-start gap-3"><span className="hidden size-11 shrink-0 items-center justify-center rounded-xl border border-slate-100 bg-slate-50 text-slate-400 sm:flex"><Building2 size={22} strokeWidth={1.4} /></span><div className="min-w-36"><p className="max-w-sm font-semibold text-ink">{property.title}</p><p className="mt-1.5 flex items-start gap-1 text-xs leading-5 text-muted"><MapPin size={12} className="mt-1 shrink-0" /><span>{property.address}</span></p><div className="mt-2 lg:hidden"><StatusBadge status={property.status} /></div></div></div></td><td className="hidden px-5 py-5 md:table-cell"><span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted">{property.operation_type === 'alquiler' ? <KeyRound size={14} /> : <ArrowUpRight size={14} />}{property.operation_type === 'alquiler' ? 'Alquiler' : 'Venta'}</span></td><td className="px-5 py-5 text-right"><p className="whitespace-nowrap text-sm font-semibold tabular-nums">{money(property.price)}</p><p className="mt-1 text-[10px] text-muted md:hidden">{property.operation_type === 'alquiler' ? 'Alquiler' : 'Venta'}</p></td><td className="hidden px-5 py-5 lg:table-cell"><StatusBadge status={property.status} /></td><td className="px-5 py-5 text-right"><button onClick={() => setForm({ property })} aria-label={`Editar ${property.title}`} title="Editar propiedad" className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-2.5 py-2 text-xs font-medium text-muted hover:border-brand/30 hover:bg-emerald-50 hover:text-brand"><Pencil size={14} /><span className="hidden xl:inline">Editar</span></button></td></tr>)}</tbody></table></div><div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 px-5 py-4 text-xs text-muted"><span>{filtered.length} {filtered.length === 1 ? 'propiedad' : 'propiedades'}{hasFilters ? ` de ${properties.length}` : ' en tu cartera'}</span>{hasFilters && <button onClick={clearFilters} className="font-medium text-brand hover:underline">Limpiar filtros</button>}</div></>}</Card>{form && <PropertyForm key={form.property?.id || 'new'} property={form.property} onClose={() => setForm(null)} onSaved={save} />}</>;
}
