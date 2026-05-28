import client from './client'

export const getRecords = (params) =>
  client.get('/records/', { params }).then((r) => r.data)

export const getRecord = (id) =>
  client.get(`/records/${id}/`).then((r) => r.data)

export const patchRecord = (id, data) =>
  client.patch(`/records/${id}/`, data).then((r) => r.data)

export const approveRecord = (id) =>
  client.post(`/records/${id}/approve/`).then((r) => r.data)

export const rejectRecord = (id, note) =>
  client.post(`/records/${id}/reject/`, { note }).then((r) => r.data)

export const flagRecord = (id, note, flag_reasons) =>
  client.post(`/records/${id}/flag/`, { note, flag_reasons }).then((r) => r.data)

export const bulkApprove = (ids) =>
  client.post('/records/bulk-approve/', { ids }).then((r) => r.data)

export const bulkReject = (ids, note) =>
  client.post('/records/bulk-reject/', { ids, note }).then((r) => r.data)

export const getRecordAudit = (id) =>
  client.get(`/records/${id}/audit/`).then((r) => r.data)

export const getDashboardSummary = () =>
  client.get('/dashboard/summary/').then((r) => r.data)

export const uploadFile = (sourceType, file) => {
  const form = new FormData()
  form.append('source_type', sourceType)
  form.append('file', file)
  return client.post('/ingest/upload/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const getRuns = (params) =>
  client.get('/ingest/runs/', { params }).then((r) => r.data)

export const getRun = (id) =>
  client.get(`/ingest/runs/${id}/`).then((r) => r.data)
