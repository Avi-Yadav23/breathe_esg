import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getRun } from '../api/records'
import RecordsTable from '../components/RecordsTable'

export default function RunDetailPage() {
  const { id } = useParams()

  const { data: run, isLoading } = useQuery({
    queryKey: ['run', id],
    queryFn: () => getRun(id),
  })

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>
  if (!run) return <div className="p-8 text-red-500">Run not found.</div>

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-1">Run: {run.original_filename}</h2>
      <p className="text-sm text-gray-500 mb-4">
        {run.source_type} · {new Date(run.uploaded_at).toLocaleString()}
      </p>

      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total', value: run.row_count_total, color: 'text-gray-900' },
          { label: 'OK', value: run.row_count_ok, color: 'text-green-600' },
          { label: 'Flagged', value: run.row_count_flagged, color: 'text-amber-600' },
          { label: 'Errors', value: run.row_count_error, color: 'text-red-600' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <RecordsTable initialFilters={{ ingestion_run: id }} />
      </div>
    </div>
  )
}
