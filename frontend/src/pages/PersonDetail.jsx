import { useCallback, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { Plus, Building2, FileText, Pencil } from 'lucide-react';
import { personApi, propertyApi, ownerApi, contractApi } from '../lib/api';
import { personName, dateLabel, money, CONTRACT_STATUSES } from '../lib/format';
import useApiData from '../hooks/useApiData';
import { Alert, Button, Card, EmptyState, Loading, PageHeading } from '../components/ui';
import { BackLink, DetailFields, EditButton, RetryError, StatusBadge } from '../components/EntityUI';
import PersonForm from '../components/PersonForm';
import OwnershipForm from '../components/OwnershipForm';

export default function PersonDetail({ mode }) {
  const { id } = useParams();
  const owners = mode === 'owners';
  const root = owners ? '/propietarios' : '/inquilinos';
  const location = useLocation();
  const [notice, setNotice] = useState(location.state?.notice || '');
  const [editing, setEditing] = useState(false);
  const [ownershipForm, setOwnershipForm] = useState(null);
  const loader = useCallback(async (signal) => {
    const [person, properties, links] = await Promise.all([personApi.get(id, signal), propertyApi.list(signal), owners ? ownerApi.list(signal) : contractApi.list(signal, { tenant_id: id })]);
    return { person, properties, links };
  }, [id, owners]);
  const { data, loading, error, reload } = useApiData(loader);
  const saved = () => { setEditing(false); setOwnershipForm(null); setNotice('Los cambios se guardaron correctamente.'); reload(); };
  if (loading) return <Loading label="Cargando detalle del contacto…" />;
  if (error) return <><BackLink to={root}>Volver al listado</BackLink><RetryError error={error} onRetry={reload} /></>;
  if (!data) return null;
  const { person, properties } = data;
  const links = owners ? data.links.filter((link) => link.person_id === person.id) : data.links;
  return <><BackLink to={root}>Volver a {owners ? 'propietarios' : 'inquilinos'}</BackLink><PageHeading eyebrow={owners ? 'Detalle de propietario / contacto' : 'Detalle de inquilino / contacto'} title={personName(person)} description={links.length ? owners ? 'Datos de contacto y participaciones en propiedades.' : 'Datos de contacto y contratos vinculados.' : 'Contacto disponible para vincular.'}><EditButton onClick={() => setEditing(true)} label="Editar contacto" /></PageHeading>{notice && <div className="mb-6"><Alert type="success" onDismiss={() => setNotice('')}>{notice}</Alert></div>}<div className="grid items-start gap-6 xl:grid-cols-[0.9fr_1.1fr]"><div className="space-y-6"><DetailFields title="Información personal" fields={[
    ['DNI', person.dni], ['CUIT / CUIL', person.cuit_cuil], ['Teléfono', person.phone], ['Email', person.email], ['Dirección', person.address], ['Notas', person.notes],
  ]} /><DetailFields title="Datos bancarios" fields={[["Alias", person.bank_alias], ["CBU", person.cbu]]} /></div><Card className="overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-5"><h2 className="text-base font-semibold">{owners ? 'Propiedades vinculadas' : 'Contratos vinculados'}</h2>{owners ? <Button variant="secondary" onClick={() => setOwnershipForm({ ownership: null })} disabled={!properties.length}><Plus size={15} />Vincular propiedad</Button> : <Link to="/contratos" state={{ createForTenant: person.id }} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold hover:bg-slate-50"><Plus size={15} />Crear contrato</Link>}</div>{!links.length ? <EmptyState icon={owners ? Building2 : FileText} title={owners ? 'Sin propiedades vinculadas' : 'Sin contratos vinculados'} description={owners ? properties.length ? 'Asigná una propiedad y su porcentaje para incorporar este contacto como propietario.' : 'Primero creá una propiedad desde la sección Propiedades.' : 'Seleccioná este contacto al crear un contrato para incorporarlo como inquilino.'} /> : <ul className="divide-y divide-slate-100">{links.map((link) => {
    const property = properties.find((item) => item.id === link.property_id);
    return <li key={link.id} className="p-5"><div className="flex items-start justify-between gap-4"><div><p className="text-sm font-semibold">{property?.title || 'Propiedad no disponible'}</p><p className="mt-1 text-xs leading-5 text-muted">{property?.address || '—'}</p></div>{owners ? <button type="button" onClick={() => setOwnershipForm({ ownership: link })} className="rounded-lg border border-slate-200 p-2 text-muted hover:text-brand" aria-label={`Editar participación en ${property?.title || 'la propiedad'}`}><Pencil size={15} /></button> : <StatusBadge value={link.status} definitions={CONTRACT_STATUSES} />}</div>{owners ? <><p className="mt-4 text-sm text-brand"><span className="font-semibold">{Number(link.ownership_percentage).toLocaleString('es-AR')}%</span> de participación</p>{link.notes && <p className="mt-2 whitespace-pre-wrap text-xs leading-6 text-muted">{link.notes}</p>}</> : <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs"><div className="text-muted"><p>{dateLabel(link.start_date)} — {dateLabel(link.end_date)}</p><p className="mt-1 font-medium text-ink">{money(link.current_rent, link.currency)} · {link.currency}</p></div><Link className="font-semibold text-brand hover:underline" to={`/contratos/${link.id}`}>Ver contrato</Link></div>}</li>;
  })}</ul>}</Card></div>{editing && <PersonForm person={person} mode={mode} onClose={() => setEditing(false)} onSaved={saved} />}{ownershipForm && <OwnershipForm person={person} ownership={ownershipForm.ownership} properties={properties} ownerships={data.links} onClose={() => setOwnershipForm(null)} onSaved={saved} />}</>;
}
