import { Navigate, useParams } from 'react-router-dom';

export default function PersonDetail({ mode }) {
  const { id } = useParams();
  return <Navigate to={`${mode === 'owners' ? '/propietarios' : '/inquilinos'}?ficha=${encodeURIComponent(id)}`} replace />;
}
