import { Link } from 'react-router-dom';
import { ArrowLeft, Pencil, Search, LoaderCircle } from 'lucide-react';
import Dialog from './Dialog';
import { Alert, Button, Card, Field, inputClasses } from './ui';

export function StatusBadge({ value, definitions }) {
  const status = definitions[value] || { label: value, classes: 'bg-slate-100 text-slate-600 ring-slate-600/10' };
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${status.classes}`}><span className="size-1.5 rounded-full bg-current" />{status.label}</span>;
}
export function SearchInput({ id, value, onChange, placeholder = 'Buscar…' }) {
  return <div className="relative"><label className="sr-only" htmlFor={id}>{placeholder}</label><Search size={17} className="absolute top-1/2 left-3.5 -translate-y-1/2 text-slate-400" /><input id={id} type="search" className={`${inputClasses} pl-10`} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} /></div>;
}
export function RetryError({ error, onRetry }) {
  return <Alert><div className="flex flex-wrap items-center justify-between gap-3"><span>{error}</span><button type="button" onClick={onRetry} className="font-semibold underline underline-offset-4">Reintentar</button></div></Alert>;
}
export function BackLink({ to, children }) {
  return <Link to={to} className="mb-5 inline-flex items-center gap-2 text-sm font-medium text-muted hover:text-brand"><ArrowLeft size={16} />{children}</Link>;
}
export function DetailFields({ title, fields, children }) {
  return <Card className="p-6"><h2 className="mb-5 text-base font-semibold">{title}</h2><dl className="grid gap-x-6 gap-y-5 sm:grid-cols-2">{fields.map(([label, value]) => <div key={label}><dt className="text-xs text-muted">{label}</dt><dd className="mt-1.5 break-words whitespace-pre-wrap text-sm font-medium">{value || '—'}</dd></div>)}</dl>{children}</Card>;
}
export function EditButton({ onClick, label = 'Editar', name = '' }) {
  return <Button variant="secondary" onClick={onClick} aria-label={name ? `Editar ${name}` : label}><Pencil size={15} />{label}</Button>;
}
export function FormShell({ title, intro, busy, error, onSubmit, onClose, children, submitLabel = 'Guardar cambios', size = 'md', submitDisabled = false }) {
  return <Dialog title={title} busy={busy} onClose={onClose} size={size}><form onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col"><div className="space-y-5 overflow-y-auto px-6 py-6">{intro && <p className="rounded-xl bg-slate-50 p-4 text-xs leading-6 text-muted">{intro}</p>}{error && <Alert>{error}</Alert>}{children}</div><div className="flex justify-end gap-3 border-t border-slate-100 bg-slate-50/50 px-6 py-5"><Button type="button" variant="secondary" disabled={busy} onClick={onClose}>Cancelar</Button><Button type="submit" disabled={busy || submitDisabled}>{busy && <LoaderCircle size={16} className="motion-safe:animate-spin" />}{busy ? 'Guardando…' : submitLabel}</Button></div></form></Dialog>;
}
export function TextField({ id, label, hint, className = '', ...props }) {
  return <Field id={id} label={label} hint={hint}><input id={id} className={`${inputClasses} ${className}`} {...props} /></Field>;
}
