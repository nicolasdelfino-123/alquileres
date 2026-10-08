import { useState } from 'react';
import { personApi } from '../lib/api';
import { FormShell, TextField } from './EntityUI';
import { Field, inputClasses } from './ui';

const fields = ['first_name', 'last_name', 'dni', 'cuit_cuil', 'phone', 'email', 'address', 'bank_alias', 'cbu', 'notes'];
export default function PersonForm({ person, mode, onClose, onSaved }) {
  const [values, setValues] = useState(() => Object.fromEntries(fields.map((field) => [field, person?.[field] || ''])));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const editing = Boolean(person);
  const change = (event) => setValues((current) => ({ ...current, [event.target.name]: event.target.value }));
  const props = (name) => ({ name, value: values[name], onChange: change, disabled: busy });
  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    if (!values.first_name.trim() || !values.last_name.trim()) { setError('El nombre y el apellido son obligatorios.'); return; }
    const body = Object.fromEntries(fields.map((field) => [field, values[field].trim() || null]));
    setBusy(true); setError('');
    try {
      const saved = editing ? await personApi.update(person.id, body) : await personApi.create(body);
      onSaved(saved, editing);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  const title = editing ? 'Editar contacto' : mode === 'owners' ? 'Nuevo propietario' : 'Nuevo inquilino';
  const intro = editing ? 'Los cambios de contacto también se reflejan en sus propiedades y contratos.' : mode === 'owners' ? 'Primero guardá los datos de contacto. En el detalle podrás vincular sus propiedades y porcentajes.' : 'Guardá los datos de contacto. Luego podrás seleccionar a esta persona al crear un contrato.';
  return <FormShell title={title} intro={intro} onSubmit={submit} onClose={onClose} busy={busy} error={error} submitLabel={editing ? 'Guardar cambios' : 'Guardar contacto'} size="lg"><div className="grid gap-5 sm:grid-cols-2"><TextField id="person-first-name" label="Nombre" required maxLength={100} autoComplete="given-name" {...props('first_name')} /><TextField id="person-last-name" label="Apellido" required maxLength={100} autoComplete="family-name" {...props('last_name')} /><TextField id="person-dni" label="DNI" maxLength={20} {...props('dni')} /><TextField id="person-cuit" label="CUIT / CUIL" maxLength={20} {...props('cuit_cuil')} /><TextField id="person-phone" label="Teléfono" type="tel" maxLength={30} autoComplete="tel" {...props('phone')} /><TextField id="person-email" label="Email" type="email" maxLength={150} autoComplete="email" {...props('email')} /></div><TextField id="person-address" label="Dirección" maxLength={200} autoComplete="street-address" {...props('address')} /><div className="border-t border-slate-100 pt-5"><p className="mb-4 text-sm font-semibold">Datos bancarios <span className="font-normal text-muted">· opcionales</span></p><div className="grid gap-5 sm:grid-cols-2"><TextField id="person-alias" label="Alias bancario" maxLength={100} {...props('bank_alias')} /><TextField id="person-cbu" label="CBU" maxLength={22} inputMode="numeric" {...props('cbu')} /></div></div><Field id="person-notes" label="Notas"><textarea id="person-notes" rows={3} className={`${inputClasses} resize-y`} {...props('notes')} /></Field></FormShell>;
}
