import { useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff, LoaderCircle, ShieldCheck, Building2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Alert, Brand, Button, Field, inputClasses, Loading } from '../components/ui';

export default function Login() {
  const { login, user, token, loading, expired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const destination = /^\/(dashboard|propiedades|propietarios(?:\/\d+)?|inquilinos(?:\/\d+)?|contratos(?:\/\d+)?)$/.test(location.state?.from || '') ? location.state.from : '/dashboard';
  useEffect(() => { document.title = 'Ingresar · Pako Inmobiliaria'; }, []);
  if (loading) return <Loading full label="Verificando tu sesión…" />;
  if (user && token) return <Navigate to={destination} replace />;
  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError('');
    try { await login({ username: username.trim(), password }); navigate(destination, { replace: true }); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  };
  return <div className="flex min-h-dvh bg-white"><aside className="relative hidden w-[46%] flex-col justify-between overflow-hidden bg-ink p-12 text-white lg:flex xl:p-16"><div className="absolute -right-40 -bottom-32 size-[640px] rounded-full border border-white/5" /><div className="absolute -right-28 -bottom-20 size-[450px] rounded-full border border-white/5" /><div className="absolute top-32 -left-40 size-[400px] rounded-full bg-emerald-700/10 blur-3xl" /><div className="relative"><Brand light /></div><div className="relative py-16"><div className="mb-8 flex size-16 items-center justify-center rounded-2xl border border-emerald-200/10 bg-emerald-300/5 text-emerald-200"><Building2 size={32} strokeWidth={1.3} /></div><p className="mb-5 text-[11px] font-semibold tracking-[0.2em] text-emerald-200 uppercase">Tu inmobiliaria, conectada</p><h1 className="max-w-md text-4xl leading-[1.18] font-medium tracking-tight xl:text-5xl">Cada propiedad.<br />Cada detalle.<br /><span className="text-emerald-200">Todo en su lugar.</span></h1><p className="mt-6 max-w-sm text-sm leading-7 text-slate-400">Un espacio para gestionar tu cartera, acompañar a tus clientes y mantener el control de tu negocio.</p></div><p className="relative text-xs text-slate-500">Pako Inmobiliaria · Administración</p></aside><main className="flex flex-1 flex-col justify-center px-6 py-12 sm:px-14"><div className="mx-auto w-full max-w-sm"><div className="mb-12 lg:hidden"><Brand /></div><p className="mb-3 text-[11px] font-semibold tracking-[0.16em] text-brand uppercase">Panel administrativo</p><h2 className="text-3xl font-semibold tracking-tight">Te damos la bienvenida</h2><p className="mt-3 text-sm leading-6 text-muted">Ingresá con tu usuario para continuar.</p><div className="mt-8 space-y-4">{expired && !error && <p role="status" className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">Tu sesión venció. Ingresá nuevamente para continuar.</p>}{error && <Alert>{error}</Alert>}</div><form onSubmit={submit} className="mt-6 space-y-5"><Field id="username" label="Usuario"><input id="username" name="username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" autoCapitalize="none" autoFocus required maxLength={100} disabled={busy} placeholder="Tu nombre de usuario" className={inputClasses} /></Field><Field id="password" label="Contraseña"><div className="relative"><input id="password" name="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required maxLength={1024} disabled={busy} placeholder="Ingresá tu contraseña" className={`${inputClasses} pr-12`} /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'} className="absolute inset-y-0 right-0 px-3 text-muted">{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></Field><Button type="submit" disabled={busy} className="mt-2 w-full">{busy ? <><LoaderCircle size={18} className="motion-safe:animate-spin" />Ingresando…</> : <>Ingresar al panel<ArrowRight size={17} /></>}</Button></form><p className="mt-7 text-center text-xs leading-6 text-muted">¿Necesitás acceso? Contactá al administrador de Pako.</p><div className="mt-12 flex items-center justify-center gap-2 border-t border-slate-100 pt-6 text-[11px] text-slate-400"><ShieldCheck size={15} />Acceso exclusivo para el equipo de Pako</div></div></main></div>;
}
