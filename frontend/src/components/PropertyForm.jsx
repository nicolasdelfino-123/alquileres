import { useState } from 'react';
import { Building2, LoaderCircle } from 'lucide-react';
import { propertyApi } from '../lib/api';
import { PROPERTY_STATUSES } from '../lib/format';
import { Alert, Button, Field, inputClasses } from './ui';
import Dialog from './Dialog';

export default function PropertyForm({ property, onClose, onSaved }) {
  const editing = Boolean(property);
  const [values, setValues] = useState({
    title: property?.title || '', address: property?.address || '', price: property?.price?.toString() || '',
    operation_type: property?.operation_type || 'alquiler', status: property?.status || 'available',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const change = (event) => setValues((current) => ({ ...current, [event.target.name]: event.target.value }));
  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    const price = values.price.trim().replace(',', '.');
    if (!values.title.trim() || !values.address.trim()) { setError('Completá el nombre y la dirección de la propiedad.'); return; }
    if (!/^\d{1,10}(\.\d{1,2})?$/.test(price)) { setError('Ingresá un precio válido, sin separadores de miles y con hasta dos decimales.'); return; }
    setBusy(true); setError('');
    const body = { ...values, title: values.title.trim(), address: values.address.trim(), price };
    try {
      const saved = editing ? await propertyApi.update(property.id, body) : await propertyApi.create(body);
      onSaved(saved, editing);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  return <Dialog title={editing ? 'Editar propiedad' : 'Nueva propiedad'} busy={busy} onClose={onClose}><form onSubmit={submit} className="flex min-h-0 flex-1 flex-col"><div className="space-y-5 overflow-y-auto px-6 py-6"><div className="flex items-center gap-3 rounded-xl bg-slate-50 p-4"><span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-white text-brand shadow-xs"><Building2 size={21} /></span><p className="text-xs leading-5 text-muted">{editing ? 'Actualizá la información de tu cartera.' : 'Completá los datos para incorporar una propiedad a tu cartera.'}</p></div>{error && <Alert>{error}</Alert>}<Field id="property-title" label="Nombre de la propiedad"><input id="property-title" name="title" value={values.title} onChange={change} disabled={busy} required maxLength={120} placeholder="Nombre para identificar la propiedad" className={inputClasses} /></Field><Field id="property-address" label="Dirección"><input id="property-address" name="address" value={values.address} onChange={change} disabled={busy} required maxLength={200} autoComplete="street-address" placeholder="Calle, número y localidad" className={inputClasses} /></Field><div className="grid gap-5 sm:grid-cols-2"><Field id="property-operation" label="Tipo de operación"><select id="property-operation" name="operation_type" value={values.operation_type} onChange={change} disabled={busy} className={inputClasses}><option value="alquiler">Alquiler</option><option value="venta">Venta</option></select></Field><Field id="property-status" label="Estado"><select id="property-status" name="status" value={values.status} onChange={change} disabled={busy} className={inputClasses}>{Object.entries(PROPERTY_STATUSES).map(([value, status]) => <option key={value} value={value}>{status.label}</option>)}</select></Field></div><Field id="property-price" label="Precio (ARS)" hint="Ingresá el importe sin separadores de miles. Se admiten hasta dos decimales."><div className="relative"><span className="absolute inset-y-0 left-4 flex items-center text-sm text-muted">$</span><input id="property-price" name="price" value={values.price} onChange={change} disabled={busy} type="text" inputMode="decimal" required pattern="[0-9]{1,10}([.,][0-9]{1,2})?" placeholder="0,00" className={`${inputClasses} pl-8`} /></div></Field></div><div className="flex justify-end gap-3 border-t border-slate-100 bg-slate-50/50 px-6 py-5"><Button type="button" variant="secondary" onClick={onClose} disabled={busy}>Cancelar</Button><Button type="submit" disabled={busy}>{busy && <LoaderCircle size={16} className="motion-safe:animate-spin" />}{busy ? 'Guardando…' : editing ? 'Guardar cambios' : 'Crear propiedad'}</Button></div></form></Dialog>;
}
