import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getRecords, bulkApprove, bulkReject } from '../api/records'
import FlagBadge from './FlagBadge'
import StatusBadge from './StatusBadge'

const ROW_BG = {
  flagged: 'bg-amber-50 hover:bg-amber-100',
  error: 'bg-red-50 hover:bg-red-100',
  approved: 'bg-green-50 hover:bg-green-100',
  rejected: 'bg-red-50 hover:bg-red-100',
  pending: 'bg-white hover:bg-gray-50',
}

export default function RecordsTable({ initialFilters = {} }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState({ scope: '', source_type: '', status: '', search: '', ...initialFilters })
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState([])

  const { data, isLoading, error } = useQuery({
    queryKey: ['records', filters, page],
    queryFn: () => getRecords({ ...filters, page }),
  })

  const bulkApproveMut = useMutation({
    mutationFn: () => bulkApprove(selected),
    onSuccess: () => { queryClient.invalidateQueries(['records']); setSelected([]) },
  })

  const bulkRejectMut = useMutation({
    mutationFn: () => bulkReject(selected, ''),
    onSuccess: () => { queryClient.invalidateQueries(['records']); setSelected([]) },
  })

  const records = data?.results || []
  const totalCount = data?.count || 0
  const totalPages = Math.ceil(totalCount / 50)

  const toggleSelect = (id) =>
    setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id])

  const toggleAll = () =>
    setSelected(selected.length === records.length ? [] : records.map((r) => r.id))

  const setFilter = (key, val) => { setFilters((f) => ({ ...f, [key]: val })); setPage(1) }

  if (isLoading) return <div className="p-8 text-gray-500">Loading records...</div>
  if (error) return <div className="p-8 text-red-500">Error loading records.</div>

  return (
    <div>
      {/* Filter bar */}
      <div className="flex flex-wrap gap-3 p-4 bg-white border-b border-gray-200">
        <input
          type="text"
          placeholder="Search facility, plant, category..."
          value={filters.search}
          onChange={(e) => setFilter('search', e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-green-400"
        />
        <select
          value={filters.source_type}
          onChange={(e) => setFilter('source_type', e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
        >
          <option value="">All Sources</option>
          <option value="sap">SAP</option>
          <option value="utility">Utility</option>
          <option value="travel">Travel</option>
        </select>
        <select
          value={filters.scope}
          onChange={(e) => setFilter('scope', e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
        >
          <option value="">All Scopes</option>
          <option value="1">Scope 1</option>
          <option value="2">Scope 2</option>
          <option value="3">Scope 3</option>
        </select>
        <select
          value={filters.status}
          onChange={(e) => setFilter('status', e.target.value)}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="flagged">Flagged</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="error">Error</option>
        </select>
        {selected.length > 0 && (
          <div className="flex gap-2 ml-auto">
            <span className="text-sm text-gray-500 self-center">{selected.length} selected</span>
            <button
              onClick={() => bulkApproveMut.mutate()}
              className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              disabled={bulkApproveMut.isPending}
            >
              Approve All
            </button>
            <button
              onClick={() => bulkRejectMut.mutate()}
              className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              disabled={bulkRejectMut.isPending}
            >
              Reject All
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-3 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selected.length === records.length && records.length > 0}
                  onChange={toggleAll}
                  className="rounded"
                />
              </th>
              <th className="px-3 py-3 text-left font-medium text-gray-600">Source</th>
              <th className="px-3 py-3 text-left font-medium text-gray-600">Scope</th>
              <th className="px-3 py-3 text-left font-medium text-gray-600">Category</th>
              <th className="px-3 py-3 text-left font-medium text-gray-600">Facility / Plant</th>
              <th className="px-3 py-3 text-left font-medium text-gray-600">Period</th>
              <th className="px-3 py-3 text-right font-medium text-gray-600">Activity</th>
              <th className="px-3 py-3 text-left font-medium text-gray-600">Unit</th>
              <th className="px-3 py-3 text-left font-medium text-gray-600">Status</th>
              <th className="px-3 py-3 text-left font-medium text-gray-600">Flags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {records.map((rec) => (
              <tr
                key={rec.id}
                className={`cursor-pointer transition-colors ${ROW_BG[rec.status] || 'bg-white hover:bg-gray-50'}`}
                onClick={() => navigate(`/records/${rec.id}`)}
              >
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selected.includes(rec.id)}
                    onChange={() => toggleSelect(rec.id)}
                    className="rounded"
                  />
                </td>
                <td className="px-3 py-2 font-medium text-gray-900 capitalize">{rec.source_type}</td>
                <td className="px-3 py-2 text-gray-600">{rec.scope ? `Scope ${rec.scope}` : '—'}</td>
                <td className="px-3 py-2 text-gray-600 capitalize">{rec.category || '—'}</td>
                <td className="px-3 py-2 text-gray-700">{rec.facility_name || rec.plant_code || '—'}</td>
                <td className="px-3 py-2 text-gray-600 whitespace-nowrap">
                  {rec.period_start ? `${rec.period_start}` : '—'}
                </td>
                <td className="px-3 py-2 text-right text-gray-900">
                  {rec.activity_value_normalized != null
                    ? parseFloat(rec.activity_value_normalized).toLocaleString(undefined, { maximumFractionDigits: 2 })
                    : '—'}
                </td>
                <td className="px-3 py-2 text-gray-500">{rec.activity_unit_normalized || '—'}</td>
                <td className="px-3 py-2"><StatusBadge status={rec.status} /></td>
                <td className="px-3 py-2">
                  {rec.flag_reasons?.map((f) => <FlagBadge key={f} flag={f} />)}
                </td>
              </tr>
            ))}
            {records.length === 0 && (
              <tr>
                <td colSpan={10} className="px-3 py-12 text-center text-gray-400">No records found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 bg-white border-t border-gray-200">
          <p className="text-sm text-gray-500">{totalCount} total records</p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Previous
            </button>
            <span className="px-3 py-1 text-sm text-gray-600">Page {page} of {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
