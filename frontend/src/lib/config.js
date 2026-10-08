export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:5000/api').replace(/\/+$/, '');
export const TOKEN_KEY = 'pako.access-token';
export const AUTH_EXPIRED_EVENT = 'pako:auth-expired';
