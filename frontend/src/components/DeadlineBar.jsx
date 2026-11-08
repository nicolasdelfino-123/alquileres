import { useSyncExternalStore } from 'react';
import { dateLabel } from '../lib/format';
import { deadlineState } from '../lib/deadline';

const formatter=new Intl.DateTimeFormat('en-CA',{timeZone:'America/Argentina/Cordoba',year:'numeric',month:'2-digit',day:'2-digit'});
const snapshot=()=>formatter.format(new Date());
const listeners=new Set();
let timer;
function subscribe(listener){
 listeners.add(listener);
 if(!timer)timer=setInterval(()=>listeners.forEach(callback=>callback()),60000);
 return ()=>{listeners.delete(listener);if(!listeners.size){clearInterval(timer);timer=null;}};
}
const tones={green:{text:'text-emerald-700',fill:'bg-emerald-500',track:'bg-emerald-100'},yellow:{text:'text-amber-700',fill:'bg-amber-400',track:'bg-amber-100'},red:{text:'text-red-700',fill:'bg-red-500',track:'bg-red-100'},neutral:{text:'text-slate-500',fill:'bg-slate-300',track:'bg-slate-100'}};
export default function DeadlineBar({dueDate,label='Vencimiento',kind='payment',completed=false,inactive=false}){
 const today=useSyncExternalStore(subscribe,snapshot,snapshot);
 const limits=kind==='contract'?{windowDays:90,warningDays:30,dangerDays:7}:{windowDays:30,warningDays:7,dangerDays:2};
 const state=deadlineState({dueDate,today,...limits,completed,inactive});
 const tone=tones[state.tone];
 return <div className="min-w-40 space-y-2" title={`${label}${dueDate?' · '+dateLabel(dueDate):''}. Amarillo: últimos ${limits.warningDays} días; rojo: últimos ${limits.dangerDays} días o vencido.`}><div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[11px]"><span className="text-muted">{label}{dueDate?` · ${dateLabel(dueDate)}`:''}</span><span className={`font-semibold ${tone.text}`}>{state.text}</span></div><div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={state.percent} aria-valuetext={state.text} className={`h-2 overflow-hidden rounded-full ${tone.track}`}><div style={{width:`${state.percent}%`}} className={`h-full rounded-full motion-safe:transition-[width] ${tone.fill}`}/></div></div>;
}
