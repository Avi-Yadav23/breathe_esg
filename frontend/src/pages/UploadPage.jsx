import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadFile } from '../api/records'

const SOURCE_TYPES = [
  { id: 'sap', label: 'SAP Fuel & Procurement', description: 'Tab-delimited ME2M/MB51 export', emoji: '⛽' },
  { id: 'utility', label: 'Utility Electricity', description: 'CSV portal export (Green Button-style)', emoji: '⚡' },
  { id: 'travel', label: 'Corporate Travel', description: 'Navan/Concur trip report CSV', emoji: '✈️' },
]

export default function UploadPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [sourceType, setSourceType] = useState(null)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const inputRef = useRef()

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) { setFile(dropped); setStep(3) }
  }

  const handleFileChange = (e) => {
    const selected = e.target.files[0]
    if (selected) { setFile(selected); setStep(3) }
  }

  const handleUpload = async () => {
    if (!file || !sourceType) return
    setUploading(true)
    setError('')
    try {
      const data = await uploadFile(sourceType, file)
      setResult(data)
      setStep(4)
    } catch (err) {
      setError(err.response?.data?.error || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Upload Data File</h2>

      {/* Step 1: Source type */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-700 mb-3">
          <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold mr-2 ${step >= 1 ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
            1
          </span>
          Select source type
        </h3>
        <div className="grid grid-cols-1 gap-3">
          {SOURCE_TYPES.map((s) => (
            <button
              key={s.id}
              onClick={() => { setSourceType(s.id); setStep(2) }}
              className={`flex items-center gap-4 p-4 border rounded-xl text-left transition-colors ${
                sourceType === s.id
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <span className="text-2xl">{s.emoji}</span>
              <div>
                <p className="font-medium text-gray-900">{s.label}</p>
                <p className="text-xs text-gray-500">{s.description}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Step 2: File upload */}
      {step >= 2 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold mr-2 ${step >= 2 ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
              2
            </span>
            Upload file
          </h3>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              dragging ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <input ref={inputRef} type="file" className="hidden" onChange={handleFileChange} accept=".csv,.txt" />
            {file ? (
              <div>
                <p className="font-medium text-gray-900">{file.name}</p>
                <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            ) : (
              <div>
                <p className="text-gray-500 mb-1">Drag and drop a file here, or click to browse</p>
                <p className="text-xs text-gray-400">.csv or .txt files</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 3: Confirm upload */}
      {step >= 3 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold mr-2 bg-green-600 text-white">
              3
            </span>
            Confirm & upload
          </h3>
          {error && (
            <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
          )}
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="px-6 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            {uploading ? 'Processing...' : 'Upload & Process'}
          </button>
        </div>
      )}

      {/* Step 4: Result */}
      {step === 4 && result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4">
          <p className="font-medium text-green-800 mb-3">Upload complete</p>
          <div className="grid grid-cols-4 gap-3 mb-4">
            {[
              { label: 'Total', value: result.row_count_total },
              { label: 'OK', value: result.row_count_ok },
              { label: 'Flagged', value: result.row_count_flagged },
              { label: 'Errors', value: result.row_count_error },
            ].map(({ label, value }) => (
              <div key={label} className="bg-white rounded-lg p-3 text-center border border-green-100">
                <p className="text-xl font-bold text-gray-900">{value}</p>
                <p className="text-xs text-gray-500">{label}</p>
              </div>
            ))}
          </div>
          <button
            onClick={() => navigate(`/records?ingestion_run=${result.ingestion_run_id}`)}
            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
          >
            View Records
          </button>
        </div>
      )}
    </div>
  )
}
