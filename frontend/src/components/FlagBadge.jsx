const FLAG_LABELS = {
  missing_quantity: 'Missing Qty',
  missing_unit: 'Missing Unit',
  bad_date: 'Bad Date',
  unknown_material: 'Unknown Material',
  unit_ambiguous: 'Unit Ambiguous',
  duplicate_period: 'Duplicate Period',
  long_billing_period: 'Long Period',
  zero_consumption: 'Zero Consumption',
  outlier_value: 'Outlier',
  unknown_airport: 'Unknown Airport',
  missing_destination: 'Missing Dest.',
  missing_travel_class: 'Missing Class',
  missing_distance: 'Missing Distance',
  unknown_plant: 'Unknown Plant',
}

export default function FlagBadge({ flag }) {
  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 mr-1 mb-1"
      title={flag}
    >
      {FLAG_LABELS[flag] || flag}
    </span>
  )
}
