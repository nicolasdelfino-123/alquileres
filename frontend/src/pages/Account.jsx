import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { Alert, Brand, Button, Field, inputClasses } from '../components/ui';

const modes = {
  register: { title: 'Creá tu cuenta', text: 'Elegí tu usuario, correo y contraseña para empezar.', endpoint: 'register', button: 'Crear cuenta' },
  forgot: { title: 'Recuperá tu contraseña', text: 'Ingresá el correo de tu cuenta para recibir un enlace de recuperación.', endpoint: 'forgot-password', button: 'Enviar enlace' },
  resend: { title: 'Verificá tu correo', text: 'Ingresá tu correo para recibir un nuevo enlace de verificación.', endpoint: 'resend-verification', button: 'Reenviar enlace' },
  verify: { title: 'Confirmá tu correo', text: 'Confirmá para habilitar tu cuenta e ingresar al panel.', endpoint: 'verify-email', button: 'Verificar correo' },
  reset: { title: 'Elegí una nueva contraseña', text: 'Usá al menos 12 caracteres. Al guardar, se cerrarán tus sesiones anteriores.', endpoint: 'reset-password', button: 'Guardar contraseña' },
};

export default function Account() {
  const [params] = useSearchParams();
  const action = params.get('action') || 'register';
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('token') || params.get('token') || '');
  useEffect(() => {
    if (token) window.history.replaceState(null, '', `/cuenta?action=${encodeURIComponent(action)}`);
  }, [token, action]);
  // Remount the form when navigating between account actions.
  return <AccountForm key={`${action}:${token}`} action={action} token={token} />;
}

function AccountForm({ action, token }) {
  const mode = modes[action];
  const [values, setValues] = useState({ username: '', email: '', password: '', confirmation: '' });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    document.title = `${mode?.title || 'Cuenta'} · Bricks Bienes Raíces`;
    const previous = document.querySelector('meta[name="referrer"]');
    const meta = previous || document.createElement('meta');
    const original = meta.content;
    meta.name = 'referrer'; meta.content = 'no-referrer';
    if (!previous) document.head.appendChild(meta);
    return () => { if (previous) meta.content = original; else meta.remove(); };
  }, [mode]);
  const hasPassword = action === 'register' || action === 'reset';
  const props = (name) => ({ value: values[name], onChange: (event) => setValues({ ...values, [name]: event.target.value }), disabled: busy, className: inputClasses, required: true });
  const submit = async (event) => {
    event.preventDefault();
    if (busy || !mode) return;
    setError('');
    if (hasPassword && values.password !== values.confirmation) { setError('Las contraseñas no coinciden.'); return; }
    setBusy(true);
    try {
      const body = action === 'register' ? { username: values.username.trim(), email: values.email.trim(), password: values.password }
        : action === 'reset' ? { token, password: values.password }
        : action === 'verify' ? { token } : { email: values.email.trim() };
      const result = await api(`/auth/${mode.endpoint}`, { method: 'POST', body, auth: false });
      setMessage(result.message);
      setValues({ username: '', email: '', password: '', confirmation: '' });
    } catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  return <main className="flex min-h-dvh items-center justify-center bg-slate-50 px-6 py-12"><div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm"><Brand /><h1 className="mt-8 text-2xl font-semibold">{mode?.title || 'Enlace inválido'}</h1><p className="mt-3 text-sm leading-6 text-muted">{mode?.text || 'Solicitá un enlace nuevo desde el inicio de sesión.'}</p>{error && <div className="mt-5"><Alert>{error}</Alert></div>}{message ? <p role="status" className="mt-6 rounded-xl bg-emerald-50 p-4 text-sm text-brand">{message}</p> : mode && <form onSubmit={submit} className="mt-6 space-y-5">{action === 'register' && <Field id="account-username" label="Usuario"><input id="account-username" autoComplete="username" maxLength={100} {...props('username')} /></Field>}{['register', 'forgot', 'resend'].includes(action) && <Field id="account-email" label="Correo electrónico"><input id="account-email" type="email" autoComplete="email" maxLength={150} {...props('email')} /></Field>}{hasPassword && <><Field id="account-password" label="Contraseña (mínimo 12 caracteres)"><input id="account-password" type="password" autoComplete="new-password" minLength={12} maxLength={1024} {...props('password')} /></Field><Field id="account-confirmation" label="Repetí la contraseña"><input id="account-confirmation" type="password" autoComplete="new-password" minLength={12} maxLength={1024} {...props('confirmation')} /></Field></>}<Button type="submit" className="w-full" disabled={busy || (['verify', 'reset'].includes(action) && !token)}>{busy ? 'Procesando…' : mode.button}</Button></form>}<div className="mt-6 space-y-3 text-center text-sm"><Link to="/login" className="block font-semibold text-brand">Volver a iniciar sesión</Link>{action === 'verify' && <Link to="/cuenta?action=resend" className="block text-muted">Reenviar correo de verificación</Link>}{action === 'reset' && <Link to="/cuenta?action=forgot" className="block text-muted">Solicitar un nuevo enlace</Link>}</div></div></main>;
}
