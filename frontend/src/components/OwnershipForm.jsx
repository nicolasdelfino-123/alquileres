import { useState } from 'react';
import { ownerApi } from '../lib/api';
import { decimalInput } from '../lib/format';
import { FormShell, TextField } from './EntityUI';
import { Field, inputClasses } from './ui';

export default function OwnershipForm({ person, ownership, properties, ownerships, onClose, onSaved }) {
  const editing = Boolean(ownership);
  const [propertyId, setPropertyId] = useState(String(ownership?.property_id || ''));
  const [percentage, setPercentage] = useState(ownership?.ownership_percentage || '100.00');
  const [notes, setNotes] = useState(ownership?.notes || '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const available = properties.filter((property) => editing ? property.id === ownership.property_id : !ownerships.some((item) => item.property_id === property.id && item.person_id === person.id));
  const assigned = ownerships.filter((item) => item.property_id === Number(propertyId) && item.id !== ownership?.id).reduce((sum, item) => sum + Math.round(Number(item.ownership_percentage) * 100), 0);
  const remaining = Math.max(0, 10000 - assigned);
  const selectProperty = (value) => {
    setPropertyId(value);
    const other = ownerships.filter((item) => item.property_id === Number(value)).reduce((sum, item) => sum + Math.round(Number(item.ownership_percentage) * 100), 0);
    setPercentage((Math.max(0, 10000 - other) / 100).toFixed(2));
  };
  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    const value = decimalInput(percentage, 3);
    if (!propertyId || !available.some((property) => property.id === Number(propertyId))) { setError('Seleccioná una propiedad disponible para vincular.'); return; }
    if (value === null || Number(value) > 100) { setError('El porcentaje debe estar entre 0 y 100, con hasta dos decimales.'); return; }
    if (Math.round(Number(value) * 100) + assigned > 10000) { setError('La suma de porcentajes de esta propiedad supera el 100%.'); return; }
    setBusy(true); setError('');
    const body = { property_id: Number(propertyId), person_id: person.id, ownership_percentage: value, notes: notes.trim() || null };
    try {
      const saved = editing ? await ownerApi.update(ownership.id, body) : await ownerApi.create(body);
      onSaved(saved, editing);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  return <FormShell title={editing ? 'Editar participación' : 'Vincular propiedad'} intro="Asigná la propiedad y su participación. La suma entre todos los propietarios no puede superar el 100%." busy={busy} error={error} onClose={onClose} onSubmit={submit} submitLabel={editing ? 'Guardar participación' : 'Vincular propiedad'}><Field id="ownership-property" label="Propiedad"><select id="ownership-property" required value={propertyId} onChange={(event) => selectProperty(event.target.value)} disabled={busy || editing} className={inputClasses}><option value="">Seleccioná una propiedad</option>{available.map((property) => <option key={property.id} value={property.id}>{property.title} · {property.address}</option>)}</select>{!available.length && <p className="mt-2 text-xs text-muted">No hay propiedades nuevas para vincular.</p>}</Field><TextField id="ownership-percentage" label="Participación (%)" required inputMode="decimal" value={percentage} onChange={(event) => setPercentage(event.target.value)} disabled={busy} hint={propertyId ? `Disponible para esta participación: ${(remaining / 100).toLocaleString('es-AR', { maximumFractionDigits: 2 })}%.` : 'Seleccioná una propiedad para consultar la participación disponible.'} /><Field id="ownership-notes" label="Notas"><textarea id="ownership-notes" value={notes} onChange={(event) => setNotes(event.target.value)} disabled={busy} rows={3} className={`${inputClasses} resize-y`} /></Field></FormShell>;
}
