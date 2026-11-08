import { API_URL, AUTH_EXPIRED_EVENT, TOKEN_KEY } from './config';

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

export async function api(path, { body, formData, method = 'GET', auth = true, signal } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth) {
    const token = sessionStorage.getItem(TOKEN_KEY);
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method, headers, signal, ...(formData ? { body: formData } : body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError('No pudimos conectar con el servidor. Revisá la conexión e intentá nuevamente.', 0);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && auth) window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
    throw new ApiError(data?.error || `No se pudo completar la solicitud (${response.status}).`, response.status);
  }
  return data;
}

export const authApi = {
  login: (credentials) => api('/auth/login', { method: 'POST', body: credentials, auth: false }),
  me: (signal) => api('/auth/me', { signal }),
};
export const propertyApi = {
  list: (signal) => api('/properties', { signal }),
  create: (values) => api('/properties', { method: 'POST', body: values }),
  update: (id, values) => api(`/properties/${id}`, { method: 'PUT', body: values }),
};
export const dashboardApi = (filters, signal) => api(`/dashboard?${new URLSearchParams(filters)}`, { signal });

function resourceApi(path) {
  return {
    list: (signal, filters) => api(`${path}${filters ? `?${new URLSearchParams(filters)}` : ''}`, { signal }),
    get: (id, signal) => api(`${path}/${id}`, { signal }),
    create: (values) => api(path, { method: 'POST', body: values }),
    update: (id, values) => api(`${path}/${id}`, { method: 'PUT', body: values }),
  };
}
export const personApi = resourceApi('/persons');
export const ownerApi = resourceApi('/property-owners');
export const contractApi = resourceApi('/contracts');
export const chargeApi = { list: (contractId, signal) => api(`/charges?${new URLSearchParams({ contract_id: contractId })}`, { signal }) };

export const workspaceApi = (filters, signal) => api(`/workspace?${new URLSearchParams(filters)}`, { signal });
export const financeApi = {
  generate: (body) => api('/charges/generate', { method: 'POST', body }),
  payment: (body) => api('/payments', { method: 'POST', body }),
  settlement: (body) => api('/settlements', { method: 'POST', body }),
  transfer: (body) => api('/transfers', { method: 'POST', body }),
  adjust: (id, body) => api(`/contracts/${id}/apply-adjustment`, { method: 'POST', body }),
  cancel: (resource, id, reason) => api(`/${resource}/${id}/cancel`, { method: 'POST', body: { reason } }),
};
export const expenseApi = resourceApi('/expenses');
export const reminderApi = resourceApi('/reminders');
export const documentApi = {
  list: (signal, filters) => api(`/documents?${new URLSearchParams(filters || {})}`, { signal }),
  upload: (formData) => api('/files', { method: 'POST', formData }),
  link: (body) => api('/documents', { method: 'POST', body }),
};
export async function downloadDocument(document) {
  if (document.file_path.startsWith('https://')) { window.open(document.file_path, '_blank', 'noopener,noreferrer'); return; }
  const token = sessionStorage.getItem(TOKEN_KEY);
  const response = await fetch(`${API_URL}/files/${document.id}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error('No se pudo descargar el archivo.');
  const url = URL.createObjectURL(await response.blob());
  const link = window.document.createElement('a'); link.href = url; link.download = document.original_filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

export async function documentFile(document) {
  const token=sessionStorage.getItem(TOKEN_KEY);
  const response=await fetch(`${API_URL}/files/${document.id}`,{headers:{Authorization:`Bearer ${token}`}});
  if(!response.ok)throw new Error('No se pudo preparar uno de los comprobantes.');
  const blob=await response.blob();
  return new File([blob],document.original_filename,{type:blob.type});
}
