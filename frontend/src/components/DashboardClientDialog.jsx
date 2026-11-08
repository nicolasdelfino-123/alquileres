import { useEffect, useState } from 'react';
import Dialog from './Dialog';
import { api } from '../lib/api';
import { dateLabel, money, personName } from '../lib/format';
import { Alert, Button, Loading } from './ui';
import { DetailFields } from './EntityUI';

export default function DashboardClientDialog({ row, field, currency, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const get = (path) => api(path, { signal: controller.signal });
    setData(null); setError('');
    (async () => {
      const personId = Number(row.person_href?.split('/').at(-1));
      const [person, expense, contracts] = await Promise.all([
        personId ? get(`/persons/${personId}`) : null,
        field === 'expenses' ? get(`/expenses/${row.id}`) : null,
        Promise.all((row.contract_ids || []).map((id) => get(`/contracts/${id}`))),
      ]);
      const propertyIds = [...new Set([...contracts.map((contract) => contract.property_id), ...(expense?.property_id ? [expense.property_id] : [])])];
      const properties = await Promise.all(propertyIds.map((id) => get(`/properties/${id}`)));
      const contactIds = [...new Set([...contracts.flatMap((contract) => contract.tenant_ids || [contract.tenant_id]), ...properties.flatMap((property) => (property.ownerships || []).map((owner) => owner.person_id))])].filter((id) => id && id !== personId);
      const contacts = await Promise.all(contactIds.map((id) => get(`/persons/${id}`)));
      if (!controller.signal.aborted) setData({ person, expense, contracts, properties, contacts: [...contacts, ...(person ? [person] : [])] });
    })().catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); });
    return () => controller.abort();
  }, [row, field, retry]);
  const name = (id) => personName(data.contacts.find((person) => person.id === id));
  return <Dialog title={field === 'expenses' ? 'Detalle del gasto' : data?.person ? personName(data.person) : 'Ficha del cliente'} size="lg" onClose={onClose}><div className="space-y-5 p-5 sm:p-6">
    {error ? <><Alert>{error}</Alert><Button variant="secondary" onClick={() => setRetry((value) => value + 1)}>Reintentar</Button></> : !data ? <Loading label="Abriendo ficha del cliente…"/> : <>
      {data.person && <DetailFields title={field === 'administration_fees' ? 'Datos del propietario' : 'Datos del inquilino'} fields={[["Nombre", personName(data.person)], ["DNI", data.person.dni], ["CUIT / CUIL", data.person.cuit_cuil], ["Teléfono", data.person.phone], ["Email", data.person.email], ["Domicilio", data.person.address], ["Ocupación", data.person.occupation], ["Alias", data.person.bank_alias], ["CBU", data.person.cbu]]}/>}
      <DetailFields title="Movimiento consultado" fields={[["Concepto", row.label], [field === 'pending' ? 'Vencimiento' : 'Fecha', dateLabel(row.date)], ["Importe", money(row.amount, currency)], ["Detalle", row.note], ...(data.expense ? [["Observaciones", data.expense.notes]] : [])]}/>
      {data.properties.map((property) => <DetailFields key={property.id} title="Propiedad relacionada" fields={[["Dirección", property.address], ["Unidad", property.unit], ["Localidad", property.city], ["Provincia", property.province], ["Propietarios", (property.ownerships || []).map((owner) => `${name(owner.person_id)} (${owner.ownership_percentage}%)`).join(' · ')]]}/>)}
      {data.contracts.map((contract) => <DetailFields key={contract.id} title={`Contrato #${contract.id}`} fields={[["Inquilinos", (contract.tenant_ids || [contract.tenant_id]).map(name).join(' · ')], ["Inicio", dateLabel(contract.start_date)], ["Finalización", dateLabel(contract.end_date)], ["Alquiler actual", money(contract.current_rent, contract.currency)], ["Día de pago", contract.payment_day], ["Índice de ajuste", contract.adjustment_index], ["Frecuencia de ajuste", contract.adjustment_frequency_months ? `${contract.adjustment_frequency_months} meses` : null], ["Próximo ajuste", contract.next_adjustment_date ? dateLabel(contract.next_adjustment_date) : null], ["Honorarios", contract.administration_percentage != null ? `${contract.administration_percentage}%` : null]]}/>)}
      {data.person?.notes && <p className="whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-sm text-muted">{data.person.notes}</p>}
      <div className="flex justify-end"><Button variant="secondary" onClick={onClose}>Cerrar ficha</Button></div>
    </>}
  </div></Dialog>;
}
