import { AlertCircle, CheckCircle2, LoaderCircle, X, Building2 } from 'lucide-react';

export function Brand({ light = false }) {
  return <div className="flex items-center gap-3"><span className={`flex size-10 items-center justify-center rounded-xl ${light ? 'bg-white/10 text-emerald-200' : 'bg-ink text-emerald-200'}`}><Building2 size={23} strokeWidth={1.7} /></span><div><span className={`block text-[23px] leading-none font-bold tracking-[0.08em] ${light ? 'text-white' : 'text-ink'}`}>PAKO<span className="text-emerald-400">.</span></span><span className={`mt-1 block text-[10px] font-medium tracking-[0.18em] uppercase ${light ? 'text-slate-400' : 'text-muted'}`}>Inmobiliaria</span></div></div>;
}
export function Button({ children, variant = 'primary', className = '', ...props }) {
  const styles = { primary: 'bg-brand text-white hover:bg-brand-dark shadow-sm', secondary: 'border border-slate-200 bg-white text-ink hover:bg-slate-50', ghost: 'text-muted hover:bg-slate-100 hover:text-ink' };
  return <button className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition-colors disabled:opacity-50 ${styles[variant]} ${className}`} {...props}>{children}</button>;
}
export function Card({ children, className = '', ...props }) {
  return <div className={`rounded-2xl border border-slate-200/80 bg-white shadow-xs ${className}`} {...props}>{children}</div>;
}
export function Alert({ children, type = 'error', onDismiss }) {
  const Icon = type === 'success' ? CheckCircle2 : AlertCircle;
  return <div role={type === 'error' ? 'alert' : 'status'} className={`flex items-start gap-3 rounded-xl border p-4 text-sm ${type === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'}`}><Icon size={18} className="mt-0.5 shrink-0" /><div className="flex-1">{children}</div>{onDismiss && <button type="button" aria-label="Cerrar mensaje" onClick={onDismiss}><X size={18} /></button>}</div>;
}
export function Loading({ label = 'Cargando…', full = false }) {
  return <div role="status" className={`flex items-center justify-center gap-3 text-sm text-muted ${full ? 'min-h-screen' : 'py-16'}`}><LoaderCircle size={21} className="motion-safe:animate-spin" />{label}</div>;
}
export function EmptyState({ icon: Icon = Building2, title, description, children }) {
  return <div className="flex flex-col items-center px-6 py-16 text-center"><div className="mb-5 flex size-16 items-center justify-center rounded-2xl bg-slate-50 text-slate-400"><Icon size={30} strokeWidth={1.4} /></div><h3 className="text-base font-semibold">{title}</h3><p className="mt-2 max-w-sm text-sm leading-6 text-muted">{description}</p>{children && <div className="mt-6">{children}</div>}</div>;
}
export const inputClasses = 'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-ink placeholder:text-slate-400 focus:border-brand focus:outline-none focus:ring-3 focus:ring-brand/10 disabled:bg-slate-50';
export function Field({ label, id, hint, children }) {
  return <div><label htmlFor={id} className="mb-2 block text-sm font-medium text-ink">{label}</label>{children}{hint && <p className="mt-2 text-xs leading-5 text-muted">{hint}</p>}</div>;
}
export function PageHeading({ eyebrow, title, description, children }) {
  return <div className="mb-7 flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div>{eyebrow && <p className="mb-2 text-[11px] font-semibold tracking-[0.16em] text-brand uppercase">{eyebrow}</p>}<h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{title}</h1><p className="mt-2 text-sm leading-6 text-muted">{description}</p></div>{children}</div>;
}
