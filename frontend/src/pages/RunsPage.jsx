import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getRuns } from '../api/records'

export default function RunsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({
    queryKey: ['runs', page],
    queryFn: () => getRuns({ page }),
  })

  const runs = data?.results || []
  const totalPages = Math.ceil((data?.count || 0) / 50)

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Ingestion Runs</h2>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">File</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Source</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Total</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">OK</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Flagged</th>
              <th className="px-4 py-3 text-right font-medium text-gray-600">Errors</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Uploaded by</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {runs.map((run) => (
              <tr key={run.id} className="hover:bg-gray-50">
                <td className="px-4 py-2">
                  <Link to={`/runs/${run.id}`} className="text-green-600 hover:underline truncate block max-w-xs">
                    {run.original_filename}
                  </Link>
                </td>
                <td className="px-4 py-2 text-gray-600 capitalize">{run.source_type}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    run.status === 'complete' ? 'bg-green-100 text-green-700' :
                    run.status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>{run.status}</span>
                </td>
                <td className="px-4 py-2 text-right text-gray-700">{run.row_count_total}</td>
                <td className="px-4 py-2 text-right text-green-600">{run.row_count_ok}</td>
                <td className="px-4 py-2 text-right text-amber-600">{run.row_count_flagged}</td>
                <td className="px-4 py-2 text-right text-red-500">{run.row_count_error}</td>
                <td className="px-4 py-2 text-gray-500">{run.uploaded_by?.username || '—'}</td>
                <td className="px-4 py-2 text-gray-500 whitespace-nowrap">
                  {new Date(run.uploaded_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-12 text-center text-gray-400">No ingestion runs yet.</td>
              </tr>
            )}
          </tbody>
        </table>
        {totalPages > 1 && (
          <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-200">
            <button
              onClick={() => setPage((p) => p - 1)}
              disabled={page === 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page === totalPages}
              className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
