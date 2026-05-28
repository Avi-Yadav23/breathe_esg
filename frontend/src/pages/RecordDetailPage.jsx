import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRecord, patchRecord, approveRecord, rejectRecord, getRecordAudit,
} from '../api/records'
import FlagBadge from '../components/FlagBadge'
import StatusBadge from '../components/StatusBadge'

export default function RecordDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [editValues, setEditValues] = useState({})
  const [rejectNote, setRejectNote] = useState('')
  const [showRaw, setShowRaw] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)

  const { data: rec, isLoading } = useQuery({
    queryKey: ['record', id],
    queryFn: () => getRecord(id),
  })

  const { data: auditLogs } = useQuery({
    queryKey: ['audit', id],
    queryFn: () => getRecordAudit(id),
  })

  const invalidate = () => {
    queryClient.invalidateQueries(['record', id])
    queryClient.invalidateQueries(['audit', id])
    queryClient.invalidateQueries(['records'])
  }

  const saveMut = useMutation({
    mutationFn: (data) => patchRecord(id, data),
    onSuccess: () => { setEditing(false); invalidate() },
  })

  const approveMut = useMutation({
    mutationFn: () => approveRecord(id),
    onSuccess: invalidate,
  })

  const rejectMut = useMutation({
    mutationFn: () => rejectRecord(id, rejectNote),
    onSuccess: () => { setShowRejectModal(false); invalidate() },
  })

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>
  if (!rec) return <div className="p-8 text-red-500">Record not found.</div>

  const isLocked = !!rec.locked_at

  const startEdit = () => {
    setEditValues({
      activity_value: rec.activity_value || '',
      activity_unit_normalized: rec.activity_unit_normalized || '',
      analyst_note: rec.analyst_note || '',
    })
    setEditing(true)
  }

  return (
    <div className="p-6 max-w-3xl">
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 flex items-center gap-1"
      >
        ← Back
      </button>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Record Detail</h2>
          <p className="text-xs text-gray-400 mt-1 font-mono">{rec.id}</p>
        </div>
        <div className="flex items-center gap-2">
          {isLocked && (
            <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full font-medium">
              Locked for audit
            </span>
          )}
          <StatusBadge status={rec.status} />
        </div>
      </div>

      {/* Flags */}
      {rec.flag_reasons?.length > 0 && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-xs font-medium text-amber-800 mb-1">Flags</p>
          {rec.flag_reasons.map((f) => <FlagBadge key={f} flag={f} />)}
        </div>
      )}

      {/* Fields */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Activity Data</h3>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          {[
            ['Source', rec.source_type],
            ['Scope', rec.scope ? `Scope ${rec.scope}` : '—'],
            ['Category', rec.category || '—'],
            ['Subcategory', rec.travel_subcategory || '—'],
            ['Period Start', rec.period_start || '—'],
            ['Period End', rec.period_end || '—'],
            ['Facility', rec.facility_name || '—'],
            ['Plant Code', rec.plant_code || '—'],
            ['Country', rec.location_country || '—'],
            ['Origin IATA', rec.origin_iata || '—'],
            ['Destination IATA', rec.destination_iata || '—'],
            ['Travel Class', rec.travel_class || '—'],
            ['Distance (km)', rec.distance_km || '—'],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-gray-500">{label}</dt>
              <dd className="font-medium text-gray-900 capitalize">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Editable section */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700">Normalized Values</h3>
          {!isLocked && !editing && (
            <button onClick={startEdit} className="text-xs text-green-600 hover:underline">Edit</button>
          )}
        </div>
        {editing ? (
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Activity Value</label>
              <input
                type="number"
                value={editValues.activity_value}
                onChange={(e) => setEditValues((v) => ({ ...v, activity_value: e.target.value }))}
                className="border border-gray-300 rounded px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-green-400"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Normalized Unit</label>
              <input
                type="text"
                value={editValues.activity_unit_normalized}
                onChange={(e) => setEditValues((v) => ({ ...v, activity_unit_normalized: e.target.value }))}
                className="border border-gray-300 rounded px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-green-400"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Analyst Note</label>
              <textarea
                value={editValues.analyst_note}
                onChange={(e) => setEditValues((v) => ({ ...v, analyst_note: e.target.value }))}
                rows={3}
                className="border border-gray-300 rounded px-3 py-1.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-green-400"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => saveMut.mutate(editValues)}
                disabled={saveMut.isPending}
                className="px-4 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
              >
                Save
              </button>
              <button onClick={() => setEditing(false)} className="px-4 py-1.5 text-sm text-gray-600 hover:text-gray-900">
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div>
              <dt className="text-gray-500">Activity Value (raw)</dt>
              <dd className="font-medium text-gray-900">{rec.activity_value ?? '—'} {rec.activity_unit}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Activity Value (normalized)</dt>
              <dd className="font-medium text-gray-900">{rec.activity_value_normalized ?? '—'} {rec.activity_unit_normalized}</dd>
            </div>
            <div className="col-span-2">
              <dt className="text-gray-500">Analyst Note</dt>
              <dd className="font-medium text-gray-700">{rec.analyst_note || '—'}</dd>
            </div>
            {rec.is_edited && (
              <div className="col-span-2">
                <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">Manually edited</span>
              </div>
            )}
          </dl>
        )}
      </div>

      {/* Actions */}
      {!isLocked && (
        <div className="flex gap-3 mb-4">
          <button
            onClick={() => approveMut.mutate()}
            disabled={approveMut.isPending}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 font-medium"
          >
            Approve & Lock
          </button>
          <button
            onClick={() => setShowRejectModal(true)}
            className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 font-medium"
          >
            Reject
          </button>
        </div>
      )}

      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-xl">
            <h3 className="font-semibold text-gray-900 mb-3">Reject Record</h3>
            <textarea
              placeholder="Reason for rejection (optional)"
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              rows={3}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-red-400"
            />
            <div className="flex gap-2">
              <button
                onClick={() => rejectMut.mutate()}
                disabled={rejectMut.isPending}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                Confirm Reject
              </button>
              <button onClick={() => setShowRejectModal(false)} className="px-4 py-2 text-sm text-gray-600">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Raw data */}
      <div className="bg-white rounded-xl border border-gray-200 mb-4">
        <button
          onClick={() => setShowRaw((s) => !s)}
          className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <span>Raw Source Data</span>
          <span className="text-gray-400">{showRaw ? '▲' : '▼'}</span>
        </button>
        {showRaw && rec.raw_record && (
          <div className="border-t border-gray-100 px-5 py-4">
            <pre className="text-xs text-gray-700 overflow-auto bg-gray-50 p-3 rounded max-h-64">
              {JSON.stringify(rec.raw_record.raw_data, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Audit log */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Audit Log</h3>
        {auditLogs?.length > 0 ? (
          <div className="space-y-3">
            {auditLogs.map((log) => (
              <div key={log.id} className="flex gap-3 text-sm">
                <div className="w-2 h-2 rounded-full bg-green-400 mt-1.5 shrink-0" />
                <div>
                  <p className="text-gray-900">
                    <span className="font-medium capitalize">{log.action.replace('_', ' ')}</span>
                    {log.actor && <span className="text-gray-500"> by {log.actor.username}</span>}
                  </p>
                  {log.note && <p className="text-gray-500 text-xs mt-0.5">{log.note}</p>}
                  <p className="text-gray-400 text-xs mt-0.5">{new Date(log.timestamp).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">No audit entries yet.</p>
        )}
      </div>
    </div>
  )
}
