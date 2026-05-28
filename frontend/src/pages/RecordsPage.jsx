import RecordsTable from '../components/RecordsTable'

export default function RecordsPage() {
  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-4">Records</h2>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <RecordsTable />
      </div>
    </div>
  )
}
