import { Outlet, NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Layout() {
  const { user, tenant, logout } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-lg font-bold text-green-700">Breathe ESG</h1>
          {tenant && <p className="text-xs text-gray-500 mt-0.5">{tenant.name}</p>}
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {[
            { to: '/dashboard', label: 'Dashboard' },
            { to: '/upload', label: 'Upload' },
            { to: '/records', label: 'Records' },
            { to: '/runs', label: 'Ingestion Runs' },
          ].map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-green-50 text-green-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-200">
          <p className="text-xs text-gray-500 mb-2">{user?.username}</p>
          <button
            onClick={logout}
            className="text-xs text-gray-400 hover:text-red-500 transition-colors"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
