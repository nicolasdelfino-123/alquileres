import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Alert, Button, Loading } from './ui';

export default function ProtectedRoute() {
  const { user, token, loading, error, retry, logout } = useAuth();
  const location = useLocation();
  if (!token) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (loading) return <Loading full label="Verificando tu sesión…" />;
  if (error) return <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-5 px-6"><Alert>{error}</Alert><Button onClick={retry}>Reintentar conexión</Button><Button variant="secondary" onClick={logout}>Volver al ingreso</Button></div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}
