export function money(value, currency = 'ARS') {
  if (value === undefined || value === null) return '—';
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency, currencyDisplay: 'narrowSymbol', maximumFractionDigits: 2 }).format(value);
}

export const MONTHS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
export const PROPERTY_STATUSES = {
  available: { label: 'Disponible', classes: 'bg-emerald-50 text-emerald-700 ring-emerald-600/10' },
  rented: { label: 'Alquilada', classes: 'bg-blue-50 text-blue-700 ring-blue-600/10' },
  sold: { label: 'Vendida', classes: 'bg-violet-50 text-violet-700 ring-violet-600/10' },
  inactive: { label: 'Inactiva', classes: 'bg-slate-100 text-slate-600 ring-slate-600/10' },
};

export const personName = (person) => person ? `${person.first_name} ${person.last_name}`.trim() : 'Contacto no disponible';
export const normalizeSearch = (value) => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
export const contractTenantIds = (contract) => contract.tenant_ids || (contract.tenant_id ? [contract.tenant_id] : []);
export const dateLabel = (value) => value ? new Intl.DateTimeFormat('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T12:00:00Z`)) : '—';
export const CONTRACT_STATUSES = {
  active: { label: 'Activo', classes: 'bg-emerald-50 text-emerald-700 ring-emerald-600/10' },
  expired: { label: 'Vencido', classes: 'bg-amber-50 text-amber-700 ring-amber-600/10' },
  terminated: { label: 'Finalizado', classes: 'bg-slate-100 text-slate-600 ring-slate-600/10' },
  cancelled: { label: 'Anulado', classes: 'bg-red-50 text-red-700 ring-red-600/10' },
};
export function decimalInput(value, integerDigits = 10) {
  const text = String(value).trim().replace(',', '.');
  if (!new RegExp(`^\\d{1,${integerDigits}}(\\.\\d{1,2})?$`).test(text)) return null;
  return text;
}
