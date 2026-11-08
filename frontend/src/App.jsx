import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Properties from './pages/Properties';
import Login from './pages/Login';
import Account from './pages/Account';
import MailSettings from './pages/MailSettings';
import People from './pages/People';
import PersonDetail from './pages/PersonDetail';
import RentalWorkspace from './pages/RentalWorkspace';
import Operations from './pages/Operations';
import BusinessResults from './pages/BusinessResults';
import WorkbookArchive from './pages/WorkbookArchive';
import ContractDetail from './pages/ContractDetail';

export default function App() {
  return <Routes><Route path="/configurar-correo" element={<MailSettings />} /><Route path="/cuenta" element={<Account />} /><Route path="/login" element={<Login />} /><Route element={<ProtectedRoute />}><Route element={<Layout />}><Route index element={<Navigate to="/dashboard" replace />} /><Route path="/dashboard" element={<Dashboard />} /><Route path="/propiedades" element={<Properties />} />
    <Route path="/propietarios" element={<People key="owners" mode="owners" />} />
    <Route path="/propietarios/:id" element={<PersonDetail key="owners" mode="owners" />} />
    <Route path="/inquilinos" element={<People key="tenants" mode="tenants" />} />
    <Route path="/inquilinos/:id" element={<PersonDetail key="tenants" mode="tenants" />} />
    <Route path="/contratos" element={<RentalWorkspace />} />
    <Route path="/alquileres" element={<RentalWorkspace />} />
    <Route path="/liquidaciones" element={<RentalWorkspace />} />
    <Route path="/gastos" element={<Operations kind="expenses" />} />
    <Route path="/alertas" element={<Operations kind="tasks" />} />
    <Route path="/ventas" element={<Operations kind="sales" />} />
    <Route path="/resultados" element={<BusinessResults />} />
    <Route path="/planillas" element={<WorkbookArchive />} />
    <Route path="/contratos/:id" element={<ContractDetail />} /></Route></Route><Route path="*" element={<Navigate to="/dashboard" replace />} /></Routes>;
}
