import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { LayoutDashboard, Building2, Users, KeyRound, FileText, Wallet, Landmark, Receipt, Handshake, Bell, Menu, LogOut, ChevronRight, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Brand } from './ui';
import Dialog from './Dialog';

const sections = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { label: 'Propiedades', icon: Building2, path: '/propiedades' },
  { label: 'Propietarios', icon: Users, path: '/propietarios' },
  { label: 'Inquilinos', icon: KeyRound, path: '/inquilinos' },
  { label: 'Contratos', icon: FileText, path: '/contratos' },
  { label: 'Alquileres y cobros', icon: Wallet },
  { label: 'Liquidaciones', icon: Landmark },
  { label: 'Gastos', icon: Receipt },
  { label: 'Compraventas', icon: Handshake },
  { label: 'Alertas', icon: Bell },
];
function Sidebar({ onNavigate, mobile = false }) {
  return <div className="flex h-full min-h-0 flex-col">{!mobile && <div className="px-7 pt-8 pb-10"><Brand light /></div>}<div className={`px-6 ${mobile ? 'pt-6' : ''}`}><p className="mb-4 text-[10px] font-semibold tracking-[0.18em] text-slate-500 uppercase">Administración</p></div><nav aria-label="Menú principal" className="space-y-1 px-3">{sections.map(({ label, icon: Icon, path }) => path ? <NavLink key={label} to={path} onClick={onNavigate} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors ${isActive ? 'bg-white/10 text-white ring-1 ring-white/5' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}><Icon size={19} strokeWidth={1.7} /><span>{label}</span><ChevronRight size={15} className="ml-auto opacity-50" /></NavLink> : <button key={label} disabled title={`${label}: próximamente`} className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-medium text-slate-500"><Icon size={19} strokeWidth={1.7} /><span className="flex-1">{label}</span><span className="text-[9px] font-normal tracking-wide text-slate-500">Próximo</span></button>)}</nav><div className="mt-auto px-6 pt-10 pb-6"><div className="rounded-xl border border-white/10 p-4"><div className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-300"><ShieldCheck size={15} className="text-emerald-300" />Espacio de trabajo</div><p className="text-[11px] leading-5 text-slate-500">Administración de Pako Inmobiliaria</p></div></div></div>;
}

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();
  const title = sections.find((item) => item.path && (item.path === location.pathname || location.pathname.startsWith(`${item.path}/`)))?.label || 'Administración';
  useEffect(() => {
    setMenuOpen(false);
    document.title = `${title} · Pako Inmobiliaria`;
  }, [location.pathname, title]);
  const date = new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'America/Argentina/Cordoba' }).format(new Date());
  return <div className="min-h-screen"><a href="#contenido" className="sr-only z-60 rounded bg-white p-3 focus:not-sr-only focus:fixed focus:top-4 focus:left-4">Ir al contenido</a><aside className="fixed inset-y-0 left-0 z-30 hidden w-64 overflow-y-auto bg-ink lg:block"><Sidebar /></aside>{menuOpen && <Dialog title="Navegación" placement="left" dark onClose={() => setMenuOpen(false)}><Sidebar mobile onNavigate={() => setMenuOpen(false)} /></Dialog>}<div className="lg:pl-64"><header className="sticky top-0 z-20 flex h-20 items-center justify-between gap-4 border-b border-slate-200/80 bg-white/95 px-4 backdrop-blur-md sm:px-8"><div className="flex min-w-0 items-center gap-3"><button className="rounded-xl p-2 text-muted hover:bg-slate-100 lg:hidden" onClick={() => setMenuOpen(true)} aria-label="Abrir menú" aria-expanded={menuOpen}><Menu size={22} /></button><div className="flex items-center gap-2 text-sm"><span className="hidden text-muted sm:inline">Administración</span><ChevronRight size={13} className="hidden text-slate-300 sm:block" /><span className="font-medium">{title}</span></div></div><div className="flex items-center gap-3 sm:gap-5"><span className="hidden text-xs text-muted xl:block">{date}</span><div className="hidden h-7 w-px bg-slate-200 sm:block" /><div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-full bg-emerald-50 text-xs font-semibold text-brand">{user.username.slice(0, 2).toUpperCase()}</span><div className="hidden sm:block"><p className="max-w-40 truncate text-sm font-semibold">{user.username}</p><p className="mt-0.5 text-[11px] text-muted">{user.role === 'admin' ? 'Administrador' : 'Operador'}</p></div></div><button onClick={logout} aria-label="Cerrar sesión" title="Cerrar sesión" className="rounded-xl p-2 text-muted hover:bg-slate-100"><LogOut size={18} /></button></div></header><main id="contenido" className="mx-auto max-w-[1500px] px-4 py-7 sm:px-8 sm:py-9 xl:px-10"><Outlet /></main><footer className="mx-auto flex max-w-[1500px] items-center justify-between border-t border-slate-200/70 px-4 py-5 text-[11px] text-slate-400 sm:px-8 xl:px-10"><span>Pako Inmobiliaria</span><span>Panel de administración</span></footer></div></div>;
}
