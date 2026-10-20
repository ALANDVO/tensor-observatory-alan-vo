import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { Loading } from '../components/Loading';
import { login } from '../api/client';

export function LoginCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const code = searchParams.get('code');
    const error = searchParams.get('error');
    
    if (code || error) {
      return;
    }
    
    navigate('/login');
  }, [navigate, searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <Loading size="lg" />
        <p className="mt-4 text-gray-500 dark:text-gray-400">Completing sign in...</p>
      </div>
    </div>
  );
}

export function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Tensor Observatory</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-2">Sign in to continue</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-8">
          <button
            onClick={login}
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Loader2 className="h-5 w-5" />
            Sign in with Keycloak
          </button>
        </div>
      </div>
    </div>
  );
}