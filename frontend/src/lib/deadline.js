export function deadlineState({dueDate, today, windowDays=30, warningDays=7, dangerDays=2, completed=false, inactive=false}) {
  if (inactive) return {tone:'neutral',percent:0,text:'Sin seguimiento activo'};
  if (completed) return {tone:'green',percent:100,text:'Resuelto'};
  if (!dueDate) return {tone:'neutral',percent:0,text:'Sin fecha definida'};
  const due=Date.parse(`${dueDate}T00:00:00Z`),now=Date.parse(`${today}T00:00:00Z`);
  if(!Number.isFinite(due)||!Number.isFinite(now))return {tone:'neutral',percent:0,text:'Sin fecha válida'};
  const days=Math.round((due-now)/86400000);
  const text=days<0?`Vencido hace ${-days} ${days===-1?'día':'días'}`:days===0?'Vence hoy':`Vence en ${days} ${days===1?'día':'días'}`;
  return {days,tone:days<=dangerDays?'red':days<=warningDays?'yellow':'green',percent:Math.max(4,Math.min(100,Math.round((windowDays-days)/windowDays*100))),text};
}
