import DeadlineBar from './DeadlineBar';
import { useEffect, useMemo, useRef, useState } from 'react';
import DashboardClientDialog from './DashboardClientDialog';
import DashboardContractSheet from './DashboardContractSheet';
import { CalendarDays, List, ChevronLeft, ChevronRight } from 'lucide-react';
import { money, dateLabel, MONTHS } from '../lib/format';

const week = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const iso = (year, month, day) => `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

export default function DashboardBreakdown({ rows, field, filters }) {
  const [client, setClient] = useState(null);
  const [view, setView] = useState('calendar');
  const [month, setMonth] = useState({ year: Number(filters.year), month: Number(filters.month) });
  const [day, setDay] = useState(null);
  const list = useRef(null);
  const groups = useMemo(() => {
    const result = new Map();
    for (const row of rows) {
      if (!result.has(row.date)) result.set(row.date, []);
      result.get(row.date).push(row);
    }
    return result;
  }, [rows]);
  useEffect(() => {
    if (day && view === 'calendar') {
      list.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
    }
  }, [day, view]);
  const first = new Date(0);
  first.setFullYear(month.year, month.month - 1, 1);
  first.setHours(12, 0, 0, 0);
  const offset = (first.getDay() + 6) % 7;
  const last = new Date(first);
  last.setMonth(last.getMonth() + 1, 0);
  const days = last.getDate();
  const shown = view === 'list' ? rows : groups.get(day) || [];
  const move = (step) => {
    const index = month.year * 12 + month.month - 1 + step;
    setMonth({ year: Math.floor(index / 12), month: index % 12 + 1 });
    setDay(null);
  };
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-xs text-muted">{field === 'pending' ? 'Organizado por vencimiento' : field === 'collections' ? 'Organizado por fecha de cobro' : field === 'expenses' ? 'Organizado por fecha del gasto' : 'Organizado por fecha de liquidación'}</p>
      <div role="group" aria-label="Vista del detalle" className="inline-flex rounded-xl bg-slate-100 p-1">
        {[['calendar', 'Calendario', CalendarDays], ['list', 'Lista', List]].map(([value, label, Icon]) => <button key={value} type="button" aria-pressed={view === value} onClick={() => setView(value)} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-brand ${view === value ? 'bg-white text-brand shadow-xs' : 'text-muted hover:text-ink'}`}><Icon size={15}/>{label}</button>)}
      </div>
    </div>
    {view === 'calendar' && <div className="rounded-2xl border border-slate-200 p-2 sm:p-4">
      <div className="mb-4 flex items-center justify-between">
        <button type="button" disabled={month.year === 1 && month.month === 1} aria-label="Mes anterior" onClick={() => move(-1)} className="rounded-lg p-2 hover:bg-slate-100 disabled:opacity-30"><ChevronLeft size={18}/></button>
        <h3 className="text-sm font-semibold">{MONTHS[month.month - 1]} {month.year}</h3>
        <button type="button" disabled={month.year === 9998 && month.month === 12} aria-label="Mes siguiente" onClick={() => move(1)} className="rounded-lg p-2 hover:bg-slate-100 disabled:opacity-30"><ChevronRight size={18}/></button>
      </div>
      <div className="grid grid-cols-7 gap-1 sm:gap-2">
        {week.map((name) => <span key={name} className="pb-2 text-center text-[10px] font-semibold text-muted sm:text-xs">{name}</span>)}
        {Array.from({ length: offset }, (_, index) => <span key={`blank-${index}`} aria-hidden="true"/>)}
        {Array.from({ length: days }, (_, index) => {
          const date = iso(month.year, month.month, index + 1);
          const records = groups.get(date) || [];
          return <button type="button" key={date} aria-pressed={day === date} aria-label={`${dateLabel(date)}: ${records.length} registros${records.length ? `, ${money(records.reduce((sum, row) => sum + Number(row.amount), 0), filters.currency)}` : ''}`} onClick={() => setDay(date)} className={`flex min-h-16 min-w-0 flex-col items-center justify-center gap-1 rounded-lg border px-0.5 py-2 text-xs transition-colors focus-visible:outline-2 focus-visible:outline-brand sm:min-h-20 ${day === date ? 'border-brand bg-brand text-white' : records.length ? 'border-emerald-100 bg-emerald-50 text-brand hover:border-emerald-400' : 'border-transparent text-slate-400 hover:bg-slate-50'}`}><span className="font-semibold">{index + 1}</span>{records.length > 0 && <><span className="text-[9px] sm:text-[11px]">{records.length} <span className="hidden sm:inline">registros</span></span><span className={`size-1 rounded-full ${day === date ? 'bg-white' : 'bg-brand'}`}/></>}</button>;
        })}
      </div>
      <p className="mt-4 text-center text-xs leading-5 text-muted">Tocá un día para ver sus movimientos debajo. El calendario muestra los registros del período seleccionado en el dashboard.</p>
    </div>}
    <section ref={list} className="scroll-mt-4 space-y-3" aria-live="polite">
      {view === 'calendar' && day && <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3"><h3 className="text-sm font-semibold">{dateLabel(day)} · {shown.length} registros</h3><strong className="text-sm text-brand">{money(shown.reduce((sum, row) => sum + Number(row.amount), 0), filters.currency)}</strong></div>}
      {shown.map((row) => <article key={row.id} className="overflow-hidden rounded-xl border border-slate-200"><button type="button" onClick={() => setClient(row)} aria-haspopup="dialog" className="block w-full p-4 text-left transition-colors hover:bg-emerald-50/50 focus-visible:outline-2 focus-visible:outline-brand"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1"><p className="break-words text-sm font-semibold">{row.label}</p>{row.person && <p className="mt-1 text-sm text-muted">{row.person}</p>}</div><strong className="text-sm tabular-nums">{money(row.amount, filters.currency)}</strong></div><p className="mt-3 text-xs text-muted">{field === 'pending' ? 'Vence: ' : ''}{dateLabel(row.date)}</p><p className="mt-1 break-words text-xs leading-5 text-muted">{row.note}</p>{field==='pending'&&<div className="mt-3"><DeadlineBar dueDate={row.date} label="Pago pendiente"/></div>}<span className="mt-3 inline-block text-xs font-semibold text-brand">{field === 'expenses' ? 'Ver detalle del gasto' : 'Ver ficha del cliente'}</span></button></article>)}
      {!shown.length && <p className="py-6 text-center text-sm text-muted">{view === 'calendar' ? day ? 'No hay movimientos en este día.' : 'Seleccioná un día del calendario.' : 'No hay registros para este período y moneda.'}</p>}
    </section>
    {client && (client.contract_ids?.length && field !== 'expenses' ? <DashboardContractSheet row={client} field={field} filters={filters} onClose={() => setClient(null)}/> : <DashboardClientDialog row={client} field={field} currency={filters.currency} onClose={() => setClient(null)}/>)}
  </div>;
}
