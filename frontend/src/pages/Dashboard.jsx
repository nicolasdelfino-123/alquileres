import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDownLeft, Clock3, BriefcaseBusiness, Receipt, ArrowRight, RefreshCw, Wallet, Building2 } from 'lucide-react';
import { dashboardApi } from '../lib/api';
import Dialog from '../components/Dialog';
import DashboardBreakdown from '../components/DashboardBreakdown';
import { money, MONTHS } from '../lib/format';
import { Alert, Button, Card, PageHeading, inputClasses } from '../components/ui';

const metrics = [
  { field: 'collections', label: 'Cobros recibidos', detail: 'Pagos registrados durante el mes', icon: ArrowDownLeft, tone: 'bg-emerald-50 text-brand' },
  { field: 'pending', label: 'Alquileres pendientes', detail: 'Saldo de mensualidades del período', icon: Clock3, tone: 'bg-amber-50 text-amber-700' },
  { field: 'administration_fees', label: 'Honorarios', detail: 'Administración en liquidaciones', icon: BriefcaseBusiness, tone: 'bg-blue-50 text-blue-700' },
  { field: 'expenses', label: 'Gastos del mes', detail: 'Gastos registrados en el período', icon: Receipt, tone: 'bg-slate-100 text-slate-600' },
];
function currentPeriod() {
  const parts = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: 'numeric', timeZone: 'America/Argentina/Cordoba' }).formatToParts(new Date());
  return { year: parts.find((part) => part.type === 'year').value, month: String(Number(parts.find((part) => part.type === 'month').value)), currency: 'ARS' };
}
export default function Dashboard() {
  const [selected, setSelected] = useState(null);
  const [breakdown, setBreakdown] = useState(null);
  const [detailError, setDetailError] = useState('');
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailRetry, setDetailRetry] = useState(0);
  const [filters, setFilters] = useState(currentPeriod);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [yearInput, setYearInput] = useState(filters.year);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setData(null);
    dashboardApi(filters, controller.signal).then(setData).catch((failure) => {
      if (failure.name !== 'AbortError') setError(failure.message);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filters, retry]);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setBreakdown(null); setDetailError(''); setDetailLoading(true);
    dashboardApi({ ...filters, detail: selected }, controller.signal).then(setBreakdown).catch((failure) => {
      if (failure.name !== 'AbortError') setDetailError(failure.message);
    }).finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    return () => controller.abort();
  }, [selected, filters, detailRetry]);
  const setFilter = (key, value) => setFilters((current) => ({ ...current, [key]: value }));
  const applyYear = () => {
    const year = Number(yearInput);
    if (Number.isInteger(year) && year >= 1 && year <= 9998) setFilter('year', String(year));
    else setYearInput(filters.year);
  };
  const yearKey = (event) => { if (event.key === 'Enter') { event.preventDefault(); event.target.blur(); } };
  return <><PageHeading eyebrow="Vista general" title="Tu negocio, en perspectiva." description="Los números que necesitás para acompañar cada decisión."><Button variant="secondary" onClick={() => setRetry((value) => value + 1)} disabled={loading}><RefreshCw size={16} className={loading ? 'motion-safe:animate-spin' : ''} />Actualizar</Button></PageHeading><div className="mb-6 flex flex-col justify-between gap-4 rounded-2xl border border-slate-200/80 bg-white px-5 py-4 sm:flex-row sm:items-center"><div><p className="text-sm font-semibold">Resumen financiero</p><p className="mt-1 text-xs text-muted">Seleccioná el período y la moneda</p></div><div className="flex flex-wrap gap-2"><label className="sr-only" htmlFor="dashboard-month">Mes</label><select id="dashboard-month" value={filters.month} onChange={(event) => setFilter('month', event.target.value)} className={`${inputClasses} w-auto min-w-32 py-2.5`}>{MONTHS.map((month, index) => <option key={month} value={index + 1}>{month}</option>)}</select><label className="sr-only" htmlFor="dashboard-year">Año</label><input id="dashboard-year" type="number" min={1} max={9998} value={yearInput} onChange={(event) => setYearInput(event.target.value)} onBlur={applyYear} onKeyDown={yearKey} className={`${inputClasses} w-24 py-2.5`} /><label className="sr-only" htmlFor="dashboard-currency">Moneda</label><select id="dashboard-currency" value={filters.currency} onChange={(event) => setFilter('currency', event.target.value)} className={`${inputClasses} w-24 py-2.5`}><option value="ARS">ARS</option><option value="USD">USD</option><option value="EUR">EUR</option></select></div></div>{error && <div className="mb-6"><Alert>{error}</Alert></div>}<div aria-busy={loading} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(({ field, label, detail, icon: Icon, tone }) => <button key={field} type="button" disabled={loading || !!error || !data} onClick={() => setSelected(field)} aria-haspopup="dialog" className="rounded-2xl border border-slate-200/80 bg-white p-5 text-left shadow-xs transition-colors hover:border-emerald-300 hover:bg-emerald-50/20 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:cursor-wait"><div className="mb-5 flex items-center justify-between gap-3"><p className="text-xs font-medium text-muted">{label}</p><span className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${tone}`}><Icon size={19} strokeWidth={1.7} /></span></div>{loading ? <div className="h-9 w-36 rounded-lg bg-slate-100 motion-safe:animate-pulse" /> : <p className="break-words text-2xl font-semibold tracking-tight" title={money(data?.[field], filters.currency)}>{money(data?.[field], filters.currency)}</p>}<p className="mt-3 text-[11px] leading-5 text-muted">{detail}</p><span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-brand">Ver detalle<ArrowRight size={13}/></span></button>)}</div><div className="mt-6 grid items-start gap-6 xl:grid-cols-[1.35fr_1fr]"><Card><div className="flex items-center justify-between border-b border-slate-100 px-6 py-5"><div><h2 className="text-base font-semibold">Detalle del período</h2><p className="mt-1 text-xs text-muted">{MONTHS[Number(filters.month) - 1]} {filters.year}</p></div><span className="rounded-lg bg-slate-50 px-3 py-1.5 text-[11px] font-semibold text-muted">{filters.currency}</span></div><div className="px-6 py-2">{metrics.map(({ field, label, icon: Icon }) => <div key={field} className="flex items-center justify-between gap-4 border-b border-slate-100 py-4 last:border-0"><div className="flex items-center gap-3"><Icon size={16} className="text-slate-400" /><span className="text-sm text-muted">{label}</span></div><span className="text-sm font-semibold tabular-nums">{loading ? '…' : money(data?.[field], filters.currency)}</span></div>)}</div><div className="mx-6 mb-6 mt-3 flex items-center justify-between gap-4 rounded-xl bg-slate-50 p-4"><div className="flex items-center gap-3"><Wallet size={19} className="text-brand" /><div><p className="text-sm font-medium">Pendiente de transferir</p><p className="mt-1 text-[11px] text-muted">Liquidaciones del período</p></div></div><span className="text-sm font-semibold tabular-nums">{loading ? '…' : money(data?.pending_owner_transfers, filters.currency)}</span></div></Card><Card className="overflow-hidden"><div className="relative overflow-hidden bg-ink px-6 py-7 text-white"><div className="absolute -top-14 -right-16 size-52 rounded-full border border-white/10" /><span className="mb-4 inline-flex size-11 items-center justify-center rounded-xl bg-white/10 text-emerald-200"><Building2 size={23} strokeWidth={1.5} /></span><h2 className="relative text-lg font-medium">Tu cartera, organizada.</h2><p className="relative mt-2 max-w-sm text-sm leading-6 text-slate-400">Consultá tus propiedades y mantené su información al día desde un solo lugar.</p></div><div className="p-6"><Link to="/propiedades" className="flex items-center justify-between rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-brand transition-colors hover:bg-emerald-100">Gestionar propiedades<ArrowRight size={17} /></Link><p className="mt-4 text-xs leading-6 text-muted">Los indicadores reflejan los registros de la moneda seleccionada. Los cobros corresponden a la fecha del pago y los pendientes al período de la mensualidad.</p></div></Card></div>{selected && <Dialog title={metrics.find((metric) => metric.field === selected)?.label} size="lg" onClose={() => setSelected(null)}><div className="space-y-5 p-5 sm:p-6"><p className="text-sm text-muted">{MONTHS[Number(filters.month)-1]} {filters.year} · {filters.currency}</p>{detailLoading ? <p role="status" className="py-10 text-center text-sm text-muted">Cargando detalle…</p> : detailError ? <div className="space-y-3"><Alert>{detailError}</Alert><Button variant="secondary" onClick={() => setDetailRetry((value) => value + 1)}>Reintentar</Button></div> : breakdown && <><div className="flex items-center justify-between gap-4 rounded-xl bg-slate-50 p-4"><span className="text-sm text-muted">{breakdown.rows.length} registros</span><strong className="text-xl">{money(breakdown[selected], filters.currency)}</strong></div><DashboardBreakdown key={`${selected}-${filters.year}-${filters.month}-${filters.currency}`} rows={breakdown.rows} field={selected} filters={filters}/><div className="flex justify-end"><Button variant="secondary" onClick={() => setSelected(null)}>Cerrar</Button></div></>}</div></Dialog>}</>;
}
