import { useCallback, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Users, Pencil, ArrowUpRight, Search } from 'lucide-react';
import { personApi, propertyApi, ownerApi, contractApi } from '../lib/api';
import { personName, normalizeSearch, contractTenantIds } from '../lib/format';
import useApiData from '../hooks/useApiData';
import { Alert, Button, Card, EmptyState, Loading, PageHeading } from '../components/ui';
import { RetryError, SearchInput } from '../components/EntityUI';
import PersonForm from '../components/PersonForm';

export default function People({ mode }) {
  const owners = mode === 'owners';
  const root = owners ? '/propietarios' : '/inquilinos';
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [scope, setScope] = useState('linked');
  const [form, setForm] = useState(null);
  const [notice, setNotice] = useState('');
  const loader = useCallback(async (signal) => {
    const [people, properties, links] = await Promise.all([personApi.list(signal), propertyApi.list(signal), owners ? ownerApi.list(signal) : contractApi.list(signal)]);
    return { people, properties, links };
  }, [owners]);
  const { data, loading, error, reload } = useApiData(loader);
  const associations = (person) => data.links.filter((link) => owners ? link.person_id === person.id : contractTenantIds(link).includes(person.id));
  const filtered = useMemo(() => {
    if (!data) return [];
    const query = normalizeSearch(search);
    return data.people.filter((person) => {
      const linked = data.links.some((link) => owners ? link.person_id === person.id : contractTenantIds(link).includes(person.id));
      return (scope === 'linked' ? linked : !linked) && normalizeSearch(`${personName(person)} ${person.dni || ''} ${person.cuit_cuil || ''} ${person.phone || ''} ${person.email || ''}`).includes(query.trim());
    }).sort((a, b) => personName(a).localeCompare(personName(b), 'es'));
  }, [data, owners, scope, search]);
  const saved = (person, editing) => {
    setForm(null);
    if (!editing) {
      navigate(`${root}/${person.id}`, { state: { notice: owners ? 'Contacto creado. Vinculá una propiedad para incorporarlo como propietario.' : 'Contacto creado. Ya podés seleccionarlo en un contrato.' } });
      return;
    }
    setNotice('Los datos de contacto se guardaron correctamente.'); reload();
  };
  return <><PageHeading eyebrow="Relaciones que importan" title={owners ? 'Propietarios' : 'Inquilinos'} description={owners ? 'Gestioná tus contactos, propiedades y participaciones.' : 'Consultá tus contactos y los contratos que comparten.'}><Button onClick={() => setForm({ person: null })}><Plus size={17} />{owners ? 'Nuevo propietario' : 'Nuevo inquilino'}</Button></PageHeading>{notice && <div className="mb-5"><Alert type="success" onDismiss={() => setNotice('')}>{notice}</Alert></div>}{error && <div className="mb-5"><RetryError error={error} onRetry={reload} /></div>}<Card className="overflow-hidden"><div className="flex flex-col justify-between gap-4 border-b border-slate-100 p-5 lg:flex-row lg:items-center"><div className="flex flex-wrap gap-1 rounded-xl bg-slate-50 p-1" role="group" aria-label="Vínculo del contacto">{[['linked', owners ? 'Con propiedades' : 'Con contratos'], ['available', 'Contactos sin vínculo']].map(([value, label]) => <button key={value} type="button" aria-pressed={scope === value} onClick={() => setScope(value)} className={`rounded-lg px-3 py-2 text-xs font-medium ${scope === value ? 'bg-white text-ink shadow-xs' : 'text-muted hover:text-ink'}`}>{label}</button>)}</div><div className="lg:w-80"><SearchInput id={`search-${mode}`} value={search} onChange={setSearch} placeholder="Buscar por nombre, DNI o contacto…" /></div></div>{scope === 'available' && <p className="border-b border-slate-100 bg-slate-50/40 px-5 py-3 text-xs leading-5 text-muted">Estos contactos todavía no tienen {owners ? 'propiedades vinculadas. Abrí su detalle para asignar una participación.' : 'contratos vinculados. Podés seleccionarlos al crear un contrato.'}</p>}{loading ? <Loading label="Cargando contactos…" /> : error ? <EmptyState title="No pudimos cargar los contactos" description="Reintentá para consultar la información actualizada." /> : !filtered.length ? <EmptyState icon={search ? Search : Users} title={search ? 'No encontramos coincidencias' : scope === 'linked' ? owners ? 'Sin propietarios vinculados' : 'Sin inquilinos vinculados' : 'Sin contactos disponibles'} description={search ? 'Probá con otro nombre, documento o dato de contacto.' : 'Creá un contacto o consultá la otra vista para gestionar sus vínculos.'}>{search && <Button variant="secondary" onClick={() => setSearch('')}>Limpiar búsqueda</Button>}</EmptyState> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">{owners ? 'Propietarios y contactos disponibles' : 'Inquilinos y contactos disponibles'}</caption><thead className="bg-slate-50/70 text-[10px] tracking-widest text-muted uppercase"><tr><th scope="col" className="px-5 py-4">Persona</th><th scope="col" className="hidden px-5 py-4 md:table-cell">Contacto</th><th scope="col" className="px-5 py-4">{owners ? 'Propiedades' : 'Contratos'}</th><th scope="col" className="px-5 py-4 text-right"><span className="sr-only">Acciones</span></th></tr></thead><tbody className="divide-y divide-slate-100">{filtered.map((person) => {
    const links = associations(person);
    const propertyNames = links.map((link) => data.properties.find((property) => property.id === link.property_id)?.title).filter(Boolean);
    return <tr key={person.id} className="hover:bg-slate-50/60"><td className="px-5 py-5"><Link className="font-semibold hover:text-brand hover:underline" to={`${root}/${person.id}`}>{personName(person)}</Link><p className="mt-1 text-xs text-muted">{person.dni ? `DNI ${person.dni}` : 'Sin DNI registrado'}</p></td><td className="hidden px-5 py-5 md:table-cell"><p className="text-xs">{person.phone || '—'}</p><p className="mt-1 text-xs text-muted">{person.email || '—'}</p></td><td className="px-5 py-5"><span className={`rounded-full px-2.5 py-1 text-xs ${links.length ? 'bg-emerald-50 text-brand' : 'bg-slate-100 text-muted'}`}>{links.length ? `${links.length} ${owners ? links.length === 1 ? 'propiedad' : 'propiedades' : links.length === 1 ? 'contrato' : 'contratos'}` : 'Sin vínculo'}</span>{propertyNames.length > 0 && <p className="mt-2 max-w-52 truncate text-xs text-muted">{propertyNames.join(', ')}</p>}</td><td className="px-5 py-5"><div className="flex justify-end gap-2"><button onClick={() => setForm({ person })} aria-label={`Editar ${personName(person)}`} className="rounded-lg border border-slate-200 p-2 text-muted hover:bg-emerald-50 hover:text-brand"><Pencil size={15} /></button><Link to={`${root}/${person.id}`} aria-label={`Ver detalle de ${personName(person)}`} className="rounded-lg border border-slate-200 p-2 text-muted hover:bg-emerald-50 hover:text-brand"><ArrowUpRight size={16} /></Link></div></td></tr>;
  })}</tbody></table><div className="border-t border-slate-100 px-5 py-4 text-xs text-muted">{filtered.length} {filtered.length === 1 ? 'contacto' : 'contactos'}</div></div>}</Card>{form && <PersonForm key={form.person?.id || 'new'} person={form.person} mode={mode} onClose={() => setForm(null)} onSaved={saved} />}</>;
}
