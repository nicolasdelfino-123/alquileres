import { useCallback, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { contractApi, personApi, propertyApi } from '../lib/api';
import { contractTenantIds, personName, dateLabel, money, CONTRACT_STATUSES } from '../lib/format';
import useApiData from '../hooks/useApiData';
import { Alert, Card, Loading, PageHeading } from '../components/ui';
import { BackLink, DetailFields, EditButton, RetryError, StatusBadge } from '../components/EntityUI';
import ContractForm from '../components/ContractForm';

export default function ContractDetail() {
  const { id } = useParams();
  const location = useLocation();
  const [editing, setEditing] = useState(false);
  const [notice, setNotice] = useState(location.state?.notice || '');
  const loader = useCallback(async (signal) => {
    const [contract, contracts, people, properties] = await Promise.all([contractApi.get(id, signal), contractApi.list(signal), personApi.list(signal), propertyApi.list(signal)]);
    return { contract, contracts, people, properties };
  }, [id]);
  const { data, loading, error, reload } = useApiData(loader);
  const saved = () => { setEditing(false); setNotice('Los cambios del contrato se guardaron correctamente.'); reload(); };
  if (loading) return <Loading label="Cargando contrato…" />;
  if (error) return <><BackLink to="/contratos">Volver a contratos</BackLink><RetryError error={error} onRetry={reload} /></>;
  if (!data) return null;
  const { contract, properties, people } = data;
  const property = properties.find((item) => item.id === contract.property_id);
  const tenants = contractTenantIds(contract).map((identifier) => people.find((person) => person.id === identifier)).filter(Boolean);
  return <><BackLink to="/contratos">Volver a contratos</BackLink><PageHeading eyebrow="Detalle del contrato" title={property?.title || 'Contrato de alquiler'} description={property?.address || 'Condiciones del contrato de alquiler.'}><EditButton onClick={() => setEditing(true)} label="Editar contrato" /></PageHeading>{notice && <div className="mb-6"><Alert type="success" onDismiss={() => setNotice('')}>{notice}</Alert></div>}<div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5"><div><p className="text-xs text-muted">Alquiler vigente</p><p className="mt-1 text-2xl font-semibold">{money(contract.current_rent, contract.currency)} <span className="text-sm font-normal text-muted">{contract.currency}</span></p></div><StatusBadge value={contract.status} definitions={CONTRACT_STATUSES} /></div><div className="grid items-start gap-6 xl:grid-cols-[1.15fr_0.85fr]"><div className="space-y-6"><DetailFields title="Condiciones del alquiler" fields={[
    ['Fecha de inicio', dateLabel(contract.start_date)], ['Fecha de finalización', dateLabel(contract.end_date)],
    ['Alquiler inicial', `${money(contract.initial_rent, contract.currency)} · ${contract.currency}`], ['Moneda', contract.currency],
    ['Frecuencia de ajuste', contract.adjustment_frequency_months ? `Cada ${contract.adjustment_frequency_months} meses` : 'Sin frecuencia definida'],
    ['Índice de ajuste', contract.adjustment_index || 'Sin índice definido'],
    ['Administración', contract.administration_percentage == null ? 'Sin porcentaje definido' : `${Number(contract.administration_percentage).toLocaleString('es-AR')}%`],
    ['Notas', contract.notes],
  ]} /></div><Card className="p-6"><h2 className="text-base font-semibold">Inquilinos del contrato</h2><p className="mt-2 text-xs leading-6 text-muted">Todos los contactos seleccionados comparten este contrato.</p><ul className="mt-5 divide-y divide-slate-100">{tenants.map((person) => <li key={person.id} className="py-4 first:pt-0"><div className="flex flex-wrap items-center justify-between gap-2"><Link to={`/inquilinos/${person.id}`} className="text-sm font-semibold hover:text-brand hover:underline">{personName(person)}</Link>{person.id === contract.tenant_id && <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-medium text-brand">Principal</span>}</div><p className="mt-2 text-xs text-muted">{person.dni ? `DNI ${person.dni}` : 'Sin DNI registrado'}</p><p className="mt-1 text-xs text-muted">{person.phone || person.email || 'Sin datos de contacto'}</p></li>)}</ul></Card></div>{editing && <ContractForm contract={contract} people={people} properties={properties} contracts={data.contracts} onClose={() => setEditing(false)} onSaved={saved} />}</>;
}
