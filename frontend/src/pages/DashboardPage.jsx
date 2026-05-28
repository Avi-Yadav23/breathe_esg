import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getDashboardSummary } from '../api/records'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'

const SCOPE_COLORS = ['#16a34a', '#2563eb', '#d97706']

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboardSummary,
  })

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>
  if (error) return <div className="p-8 text-red-500">Error loading dashboard.</div>

  const scopeData = [
    { name: 'Scope 1', value: data.by_scope?.['1'] || 0 },
    { name: 'Scope 2', value: data.by_scope?.['2'] || 0 },
    { name: 'Scope 3', value: data.by_scope?.['3'] || 0 },
  ].filter((d) => d.value > 0)

  const sourceData = Object.entries(data.by_source || {}).map(([k, v]) => ({
    name: k.charAt(0).toUpperCase() + k.slice(1),
    count: v,
  }))

  const stats = [
    { label: 'Total Records', value: data.total_records || 0, color: 'text-gray-900' },
    { label: 'Pending Review', value: data.pending || 0, color: 'text-gray-600' },
    { label: 'Flagged', value: data.flagged || 0, color: 'text-amber-600' },
    { label: 'Approved', value: data.approved || 0, color: 'text-green-600' },
    { label: 'Errors', value: data.error || 0, color: 'text-red-600' },
  ]

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-xl font-semibold text-gray-900">Dashboard</h2>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {stats.map(({ label, value, color }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className={`text-2xl font-bold ${color}`}>{value.toLocaleString()}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-4">Records by Scope</h3>
          {scopeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={scopeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {scopeData.map((_, i) => (
                    <Cell key={i} fill={SCOPE_COLORS[i % SCOPE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">No data yet</p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-4">Records by Source</h3>
          {sourceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={sourceData}>
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#16a34a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">No data yet</p>
          )}
        </div>
      </div>

      {/* Recent runs */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-700">Recent Ingestion Runs</h3>
          <Link to="/runs" className="text-xs text-green-600 hover:underline">View all</Link>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">File</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Source</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Rows</th>
              <th className="px-4 py-2 text-right text-xs font-medium text-gray-500">Flagged</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Uploaded</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(data.recent_runs || []).map((run) => (
              <tr key={run.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-gray-900 truncate max-w-xs">{run.original_filename}</td>
                <td className="px-4 py-2 text-gray-600 capitalize">{run.source_type}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    run.status === 'complete' ? 'bg-green-100 text-green-700' :
                    run.status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{run.status}</span>
                </td>
                <td className="px-4 py-2 text-right text-gray-600">{run.row_count_total}</td>
                <td className="px-4 py-2 text-right text-amber-600">{run.row_count_flagged}</td>
                <td className="px-4 py-2 text-gray-500">{new Date(run.uploaded_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {(data.recent_runs || []).length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No runs yet. Upload a file to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
