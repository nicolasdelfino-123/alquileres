import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { Alert, Brand, Button, Field, inputClasses } from '../components/ui';

export default function MailSettings() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [username, setUsername] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [canCreateAdmin, setCanCreateAdmin] = useState(false);
  const [configured, setConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  useEffect(() => {
    document.title = 'Correo del sistema · Bricks Bienes Raíces';
    const controller = new AbortController();
    api('/settings/mail', { signal: controller.signal }).then((data) => {
      setEmail(data.email); setCode(data.registration_code); setConfigured(data.configured); setCanCreateAdmin(data.can_create_admin);
    }).catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);
  const save = async (event) => {
    event.preventDefault();
    if (busy) return;
    setError(''); setMessage('');
    if (canCreateAdmin && adminPassword !== confirm) { setError('Las contraseñas de tu cuenta no coinciden.'); return; }
    setBusy(true);
    try {
      await api('/settings/mail', { method: 'POST', body: { email, password, ...(code ? { registration_code: code } : {}),
        ...(canCreateAdmin ? { username, admin_password: adminPassword } : {}) } });
      setPassword(''); setAdminPassword(''); setConfirm(''); setCanCreateAdmin(false); setConfigured(true);
      const result = await api('/settings/mail/test', { method: 'POST', body: {} });
      setMessage(result.message);
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  return <main className="flex min-h-dvh items-center justify-center bg-slate-50 px-6 py-12"><div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-sm"><Brand /><h1 className="mt-8 text-2xl font-semibold">Correo del sistema</h1><p className="mt-3 text-sm leading-6 text-muted">Configuración del administrador. Desde esta dirección se enviarán los enlaces para verificar cuentas y recuperar contraseñas.</p>{loading ? <p className="mt-6 text-muted">Cargando…</p> : <><div className="mt-5 space-y-3">{error && <Alert>{error}</Alert>}{message && <p role="status" className="rounded-xl bg-emerald-50 p-4 text-sm text-brand">{message}</p>}</div><form onSubmit={save} className="mt-6 space-y-5"><Field id="sender-email" label="Gmail que enviará los correos"><input id="sender-email" type="email" autoComplete="email" required maxLength={150} disabled={busy} value={email} onChange={(event) => setEmail(event.target.value)} className={inputClasses} /></Field><Field id="sender-password" label="Contraseña de aplicación del remitente"><input id="sender-password" type="password" autoComplete="new-password" required={!configured} disabled={busy} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={configured ? 'Dejá vacío para conservar la actual' : 'Contraseña generada por Google'} className={inputClasses} /><p className="mt-2 text-xs leading-5 text-muted">Se configura una sola vez para el sistema. Google permite generarla con la verificación en dos pasos activa. <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" className="font-semibold text-brand">Abrir configuración de Google</a></p></Field>{canCreateAdmin && <fieldset className="space-y-4 rounded-xl border border-slate-200 p-4"><legend className="px-2 text-sm font-semibold">Creá tu cuenta de administrador</legend><Field id="setup-username" label="Tu usuario"><input id="setup-username" required maxLength={100} autoComplete="username" disabled={busy} value={username} onChange={(event) => setUsername(event.target.value)} className={inputClasses} /></Field><Field id="setup-password" label="Tu contraseña de acceso al sistema"><input id="setup-password" type="password" minLength={12} maxLength={1024} required autoComplete="new-password" disabled={busy} value={adminPassword} onChange={(event) => setAdminPassword(event.target.value)} className={inputClasses} /></Field><Field id="setup-confirm" label="Repetí tu contraseña"><input id="setup-confirm" type="password" minLength={12} maxLength={1024} required autoComplete="new-password" disabled={busy} value={confirm} onChange={(event) => setConfirm(event.target.value)} className={inputClasses} /></Field></fieldset>}<Button type="submit" disabled={busy} className="w-full">{busy ? 'Guardando y enviando…' : 'Guardar y enviar prueba'}</Button></form></>}<Link to="/login" className="mt-6 block text-center text-sm font-semibold text-brand">Volver al inicio de sesión</Link></div></main>;
}
