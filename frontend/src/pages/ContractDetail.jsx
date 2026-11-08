import { Navigate, useParams } from 'react-router-dom';

export default function ContractDetail() {
  const { id } = useParams();
  return <Navigate to={`/contratos?ficha=${encodeURIComponent(id)}`} replace />;
}
