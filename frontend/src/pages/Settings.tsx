import { Shield, Key, Database, Cpu, Bell, Moon, Sun } from 'lucide-react';
import { useAuthStore } from '../hooks/useAuth';
import { logout } from '../api/client';

export function Settings() {
  const { user } = useAuthStore();

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400">Manage your account and application preferences</p>
      </div>

      {/* Account Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary-600" /> Account
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Name</label>
            <p className="text-gray-900 dark:text-white">{user?.name || 'Not set'}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Email</label>
            <p className="text-gray-900 dark:text-white">{user?.email || 'Not set'}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">User ID</label>
            <p className="text-gray-900 dark:text-white font-mono text-sm">{user?.user_id || 'Unknown'}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Roles</label>
            <div className="flex flex-wrap gap-1">
              {user?.roles.map(r => (
                <span key={r} className="px-2 py-1 text-xs rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300">
                  {r}
                </span>
              ))}
            </div>
          </div>
        </div>
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <button onClick={logout} className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
            <Key className="h-4 w-4" /> Sign Out
          </button>
        </div>
      </div>

      {/* Preferences Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Bell className="h-5 w-5 text-primary-600" /> Preferences
        </h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Dark Mode</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Use system preference or toggle manually</p>
            </div>
            <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-gray-200 dark:bg-gray-700 transition-colors">
              <span className="inline-block h-4 w-4 transform bg-white rounded-full transition-transform" />
            </button>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Compact Density</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">Reduce spacing for more content</p>
            </div>
            <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-gray-200 dark:bg-gray-700 transition-colors">
              <span className="inline-block h-4 w-4 transform bg-white rounded-full transition-transform" />
            </button>
          </div>
        </div>
      </div>

      {/* API Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Key className="h-5 w-5 text-primary-600" /> API Access
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mb-4">API tokens for programmatic access (requires operator role)</p>
        <div className="space-y-2">
          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div>
              <p className="font-mono text-sm text-gray-900 dark:text-white">to_abc123... (expires 2025-01-15)</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Last used: 2 hours ago</p>
            </div>
            <button className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">Revoke</button>
          </div>
          <button className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">Generate New Token</button>
        </div>
      </div>

      {/* About Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Cpu className="h-5 w-5 text-primary-600" /> About
        </h2>
        <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
          <p><strong>Tensor Observatory</strong> v1.0.0</p>
          <p>A high-throughput and memory-efficient inference and serving engine observability platform for LLMs</p>
          <p>Built by <strong>Alan Vo</strong> | AI & Machine Learning</p>
          <p className="text-primary-600 dark:text-primary-400">alanvo@gmail.com</p>
        </div>
      </div>
    </div>
  );
}